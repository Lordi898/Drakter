// Drakter Companion: GNOME Shell 50 extension, D-Bus API v2.
// Exposes org.drakter.Companion on the session bus for the Drakter app:
// pointer + modifiers, active/visible windows, dialog-less screenshots,
// a floating window kept above on every workspace with a click-through
// input region that never steals the focus, and global shortcuts.
// Contract: docs/floating/CONTRACT.md §3. Interface: org.drakter.Companion1.xml.
// Base: spike 02 prototype (/tmp/drakter-floating/spikes/02-gnome-extension.md).

import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Config from 'resource:///org/gnome/shell/misc/config.js';

Gio._promisify(Shell.Screenshot.prototype, 'screenshot_stage_to_content');
Gio._promisify(Shell.Screenshot, 'composite_to_stream');

const BUS_NAME = 'org.drakter.Companion';
const OBJ_PATH = '/org/drakter/Companion';
const IFACE = 'org.drakter.Companion1';
const DEBUG_IFACE = 'org.drakter.Companion1.Debug';
const ERROR_PREFIX = 'org.drakter.Companion1.Error.';
const VERSION = 2;
const CAPABILITIES = ['pointer', 'buttons', 'gestures', 'windows', 'screenshot', 'floating',
    'input-region', 'shortcuts', 'escape', 'focus', 'passthrough', 'activate'];
const MAX_RECTS = 256;
const SHOTS_PER_SECOND = 4;

const DEBUG_XML = `<node><interface name="${DEBUG_IFACE}">
  <method name="Inject"><arg name="kind" type="s" direction="in"/>
    <arg name="x" type="i" direction="in"/><arg name="y" type="i" direction="in"/>
    <arg name="code" type="u" direction="in"/></method>
  <method name="Probe"><arg name="info" type="a{sv}" direction="out"/></method></interface></node>`;

const M = Clutter.ModifierType;
const BUTTON_MASKS = [[1, M.BUTTON1_MASK], [2, M.BUTTON2_MASK], [3, M.BUTTON3_MASK]];
const ANY_BUTTON = M.BUTTON1_MASK | M.BUTTON2_MASK | M.BUTTON3_MASK;
const SUPER = M.SUPER_MASK | M.MOD4_MASK | M.HYPER_MASK | M.META_MASK;
const SHORTCUT_MODES = Shell.ActionMode.NORMAL | Shell.ActionMode.OVERVIEW | Shell.ActionMode.POPUP;

const v = {
    s: x => new GLib.Variant('s', x ?? ''),
    i: x => new GLib.Variant('i', Math.round(x ?? 0)),
    u: x => new GLib.Variant('u', x ?? 0),
    t: x => new GLib.Variant('t', x ?? 0),
    b: x => new GLib.Variant('b', !!x),
    d: x => new GLib.Variant('d', x ?? 0),
    rect: r => new GLib.Variant('(iiii)', [r.x, r.y, r.width, r.height].map(Math.round)),
};

// Errors with a D-Bus name (CONTRACT §3.4).
class ApiError extends Error {
    constructor(kind, message) {
        super(message);
        this.kind = kind; // AccessDenied | InvalidArgs | NotFound | RateLimited | Failed
    }
}

function returnError(invocation, e) {
    const kind = e instanceof ApiError ? e.kind : 'Failed';
    invocation.return_dbus_error(`${ERROR_PREFIX}${kind}`, e.message ?? String(e));
}

function unpackDict(dict) {
    const o = {};
    for (const [k, val] of Object.entries(dict))
        o[k] = val.deepUnpack();
    return o;
}

const isInt = x => Number.isInteger(x);

export default class DrakterCompanion extends Extension {
    enable() {
        this._settings = this.getSettings();
        this._uid = Gio.Credentials.new().get_unix_user();
        this._clients = new Map(); // sender -> {authed, opts, watchId, escape, passthrough, shots}
        this._floatRule = null; // {match, monitor, cover, owner}
        this._floating = new Set(); // Meta.Window
        this._reactiveSaved = new Map(); // actor -> original reactive
        this._inputMode = 'none';
        this._inputRects = [];
        this._floatFocusOn = false; // SetFloatingFocus(true) in force
        this._prevFocus = null; // last focused window that is not the floating one
        this._focusLater = 0;
        this._timeouts = new Set();
        this._stageKeyEvents = 0;
        this._blinks = 0;
        this._laters = global.compositor.get_laters();

        this._writeToken();
        this._origIsSkip = Meta.Window.prototype.is_skip_taskbar;
        this._patchSkipTaskbar();

        const xml = new TextDecoder().decode(
            this.dir.get_child('org.drakter.Companion1.xml').load_contents(null)[1]);
        this._impl = Gio.DBusExportedObject.wrapJSObject(xml, this);
        this._impl.export(Gio.DBus.session, OBJ_PATH);
        if (GLib.getenv('DRAKTER_COMPANION_DEBUG') === '1') {
            this._debugImpl = Gio.DBusExportedObject.wrapJSObject(DEBUG_XML, new DebugApi(this));
            this._debugImpl.export(Gio.DBus.session, OBJ_PATH);
            this._keymapChanges = 0;
            global.stage.context.get_backend().get_default_seat().get_keymap().connectObject('state-changed',
                () => this._keymapChanges++, this);
            global.stage.connectObject('captured-event', (_s, ev) => {
                const t = ev.type();
                if (t === Clutter.EventType.KEY_PRESS || t === Clutter.EventType.KEY_RELEASE)
                    this._stageKeyEvents++;
                return Clutter.EVENT_PROPAGATE;
            }, this);
        }
        this._ownerId = Gio.bus_own_name_on_connection(Gio.DBus.session, BUS_NAME,
            Gio.BusNameOwnerFlags.NONE, null, null);

        // Pointer motion is event-driven (no polling) via the cursor tracker.
        this._cursorTracker = global.backend.get_cursor_tracker();
        this._cursorTracker.connectObject('position-invalidated', () => this._onPointerMoved(), this);

        // Windows.
        global.display.connectObject(
            'notify::focus-window', () => this._onFocusChanged(),
            'window-created', (_d, w) => this._onWindowCreated(w),
            'restacked', () => this._windowsChanged('restacked'),
            'accelerator-activated', (_d, action) => this._onAccelerator(action, 'press'),
            'accelerator-deactivated', (_d, action) => this._onAccelerator(action, 'release'),
            this);
        global.workspace_manager.connectObject('active-workspace-changed',
            () => this._windowsChanged('workspace'), this);
        Main.layoutManager.connectObject('monitors-changed', () => this._windowsChanged('monitors'), this);
        this._onFocusChanged();

        // Shortcuts.
        for (const name of ['toggle-floating', 'ask']) {
            Main.wm.addKeybinding(name, this._settings,
                Meta.KeyBindingFlags.IGNORE_AUTOREPEAT, SHORTCUT_MODES,
                () => this._emitShortcut(name, 'press'));
        }
        this._accels = new Map(); // action -> name
        this._grabPushToTalk();
        this._settings.connectObject('changed::push-to-talk', () => this._grabPushToTalk(),
            'changed::poll-ms', () => this._syncPoll(), this);

        this._gesture = {talk: 'idle', talkSince: 0, releasedSince: 0, ask: 'idle', askSince: 0, prevMods: 0};
        this._keymap = global.stage.context.get_backend().get_default_seat().get_keymap();
        this._keymap.connectObject('state-changed', () => this._gestureStep(), this);
    }

    disable() {
        this._stopPoll();
        for (const id of this._timeouts)
            GLib.source_remove(id);
        this._timeouts.clear();
        if (this._focusLater)
            this._laters.remove(this._focusLater);
        this._focusLater = 0;
        Main.wm.removeKeybinding('toggle-floating');
        Main.wm.removeKeybinding('ask');
        for (const action of [...this._accels.keys()])
            this._ungrab(action);
        this._accels.clear();
        this._escAction = 0;
        this._pttAction = 0;
        for (const c of this._clients.values())
            Gio.bus_unwatch_name(c.watchId);
        this._clients.clear();
        this._syncIndicator();
        this._releaseFloating();
        this._unpatchSkipTaskbar();
        global.display.disconnectObject(this);
        global.workspace_manager.disconnectObject(this);
        global.stage.disconnectObject(this);
        Main.layoutManager.disconnectObject(this);
        this._cursorTracker.disconnectObject(this);
        this._keymap.disconnectObject(this);
        this._settings.disconnectObject(this);
        this._focusWin?.disconnectObject(this);
        this._focusWin = null;
        this._prevFocus = null;
        this._impl.unexport();
        this._debugImpl?.unexport();
        this._debugImpl = null;
        Gio.bus_unown_name(this._ownerId);
        try {
            Gio.File.new_for_path(this._tokenPath).delete(null);
        } catch {}
        this._impl = null;
        this._settings = null;
        this._laters = null;
    }

    // ---------- security ----------

    _writeToken() {
        const dir = GLib.build_filenamev([GLib.get_user_runtime_dir(), 'drakter-companion']);
        GLib.mkdir_with_parents(dir, 0o700);
        const info = Gio.File.new_for_path(dir).query_info('unix::uid,standard::is-symlink',
            Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, null);
        if (info.get_is_symlink() || info.get_attribute_uint32('unix::uid') !== this._uid)
            throw new Error(`${dir} is not a private directory of this user`);
        Gio.File.new_for_path(dir).set_attribute_uint32('unix::mode', 0o700,
            Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, null);
        this._token = GLib.uuid_string_random().replaceAll('-', '') +
            GLib.uuid_string_random().replaceAll('-', '');
        this._tokenPath = GLib.build_filenamev([dir, 'token']);
        const file = Gio.File.new_for_path(this._tokenPath);
        try {
            file.delete(null);
        } catch {}
        const out = file.create(Gio.FileCreateFlags.PRIVATE, null); // 0600, O_EXCL
        out.write_all(new TextEncoder().encode(this._token), null);
        out.close(null);
    }

    async _senderUid(sender) {
        const reply = await Gio.DBus.session.call('org.freedesktop.DBus', '/org/freedesktop/DBus',
            'org.freedesktop.DBus', 'GetConnectionUnixUser', new GLib.Variant('(s)', [sender]),
            new GLib.VariantType('(u)'), Gio.DBusCallFlags.NONE, -1, null);
        return reply.deepUnpack()[0];
    }

    // Returns the client record if the caller may use the API, otherwise
    // answers the invocation with AccessDenied and returns null.
    _authed(invocation) {
        const c = this._clients.get(invocation.get_sender());
        if (c?.authed)
            return c;
        returnError(invocation, new ApiError('AccessDenied', 'Call Hello(token) first'));
        return null;
    }

    // Methods that act on the floating window: only its owner (if there is one).
    _checkOwner(sender) {
        if (this._floatRule && this._floatRule.owner !== sender)
            throw new ApiError('AccessDenied', 'The floating window belongs to another connection');
    }

    _forgetClient(sender) {
        const c = this._clients.get(sender);
        if (!c)
            return;
        Gio.bus_unwatch_name(c.watchId);
        this._clients.delete(sender);
        if (c.escape)
            this._setEscape(sender, false);
        if (this._floatRule?.owner === sender)
            this._releaseFloating();
        if (c.passthrough)
            this._updateInputRegion(true);
        this._syncPoll();
        this._syncIndicator();
    }

    // ---------- panel indicator (CONTRACT §3.5) ----------

    // Visible while at least one client is authenticated, so the user always
    // sees that the global pointer and the screenshots are open. Blinks on
    // every screenshot.
    _syncIndicator() {
        const want = [...this._clients.values()].some(c => c.authed);
        if (want && !this._indicator) {
            const button = new PanelMenu.Button(0.0, 'Drakter', false);
            this._indicatorIcon = new St.Icon({
                gicon: Gio.FileIcon.new(this.dir.get_child('icons').get_child('drakter-symbolic.svg')),
                style_class: 'system-status-icon',
            });
            button.add_child(this._indicatorIcon);
            for (const text of ['Drakter está conectado',
                'Puede ver el puntero y capturar la pantalla.',
                'Desactiva la extensión para cortar el acceso.']) {
                const item = new PopupMenu.PopupMenuItem(text, {reactive: false, can_focus: false});
                button.menu.addMenuItem(item);
            }
            this._indicator = button;
            Main.panel.addToStatusArea('drakter-companion', button);
        } else if (!want && this._indicator) {
            this._indicator.destroy();
            this._indicator = null;
            this._indicatorIcon = null;
        }
    }

    _blinkIndicator() {
        this._blinks++;
        const icon = this._indicatorIcon;
        if (!icon)
            return;
        icon.remove_all_transitions();
        icon.opacity = 255;
        icon.ease({
            opacity: 40,
            duration: 120,
            mode: Clutter.AnimationMode.EASE_OUT_QUAD,
            onComplete: () => icon.ease({opacity: 255, duration: 260, mode: Clutter.AnimationMode.EASE_IN_QUAD}),
        });
    }

    // ---------- D-Bus API ----------

    get Version() {
        return VERSION;
    }

    async HelloAsync([token], invocation) {
        const sender = invocation.get_sender();
        try {
            const uid = await this._senderUid(sender);
            if (uid !== this._uid)
                throw new Error('different user');
        } catch (e) {
            returnError(invocation, new ApiError('AccessDenied', `Access denied (${e.message})`));
            return;
        }
        if (typeof token !== 'string' || token.length !== this._token.length || token !== this._token) {
            returnError(invocation, new ApiError('AccessDenied', 'Bad token'));
            return;
        }
        if (!this._clients.has(sender)) {
            const watchId = Gio.bus_watch_name_on_connection(Gio.DBus.session, sender,
                Gio.BusNameWatcherFlags.NONE, null, () => this._forgetClient(sender));
            this._clients.set(sender, {authed: true, opts: {}, watchId, lastPointer: 0, pending: 0,
                escape: false, passthrough: false, shots: []});
        }
        this._syncIndicator();
        invocation.return_value(new GLib.Variant('(a{sv})', [{
            version: v.u(VERSION),
            shell_version: v.s(Config.PACKAGE_VERSION),
            session: v.s('wayland'), // GNOME 50 has no X11 session
            poll_ms: v.u(this._settings.get_uint('poll-ms')),
            capabilities: new GLib.Variant('as', CAPABILITIES),
        }]));
    }

    GetPointerAsync(_p, invocation) {
        if (!this._authed(invocation))
            return;
        const [x, y, mods] = global.get_pointer();
        invocation.return_value(new GLib.Variant('(iiux)', [x, y, mods, GLib.get_monotonic_time()]));
    }

    SubscribeAsync([options], invocation) {
        const c = this._authed(invocation);
        if (!c)
            return;
        const o = unpackDict(options);
        c.opts = {
            pointer: !!o.pointer,
            pointerMinUs: Math.max(4, Math.min(1000, o.pointer_min_ms ?? 8)) * 1000,
            buttons: !!o.buttons,
            gestures: !!o.gestures,
            windows: !!o.windows,
        };
        this._syncPoll();
        invocation.return_value(null);
    }

    UnsubscribeAsync(_p, invocation) {
        const c = this._authed(invocation);
        if (!c)
            return;
        c.opts = {};
        this._syncPoll();
        invocation.return_value(null);
    }

    GetActiveWindowAsync(_p, invocation) {
        if (!this._authed(invocation))
            return;
        const w = global.display.get_focus_window();
        invocation.return_value(new GLib.Variant('(a{sv})', [w ? this._winInfo(w) : {}]));
    }

    ListWindowsAsync(_p, invocation) {
        if (!this._authed(invocation))
            return;
        invocation.return_value(new GLib.Variant('(aa{sv})',
            [this._visibleWindows().map((w, i) => this._winInfo(w, i))]));
    }

    GetMonitorsAsync(_p, invocation) {
        if (!this._authed(invocation))
            return;
        const cur = global.display.get_current_monitor();
        const mons = Main.layoutManager.monitors.map(m => ({
            index: v.i(m.index),
            geometry: v.rect(m),
            workarea: v.rect(Main.layoutManager.getWorkAreaForMonitor(m.index)),
            scale: v.d(global.display.get_monitor_scale(m.index)),
            primary: v.b(m.index === Main.layoutManager.primaryIndex),
            current: v.b(m.index === cur),
        }));
        invocation.return_value(new GLib.Variant('(aa{sv})', [mons]));
    }

    async ScreenshotAsync([options], invocation) {
        const c = this._authed(invocation);
        if (!c)
            return;
        let file, actors = [], saved = [];
        try {
            const o = unpackDict(options);
            const dir = this._checkDir(o.dir);
            const targets = ['area', 'monitor', 'window'].filter(k => o[k] !== undefined);
            if (targets.length > 1)
                throw new ApiError('InvalidArgs', 'Use only one of area, monitor or window');
            const sw = global.stage.width, sh = global.stage.height;
            let [x, y, w, h] = [0, 0, sw, sh];
            if (o.area !== undefined) {
                if (!Array.isArray(o.area) || o.area.length !== 4 || !o.area.every(isInt))
                    throw new ApiError('InvalidArgs', 'area must be (iiii)');
                [x, y, w, h] = o.area;
            } else if (o.monitor !== undefined) {
                const m = Main.layoutManager.monitors[o.monitor];
                if (!m)
                    throw new ApiError('NotFound', `No monitor ${o.monitor}`);
                [x, y, w, h] = [m.x, m.y, m.width, m.height];
            } else if (o.window !== undefined) {
                const win = this._findWindow(o.window);
                if (!win)
                    throw new ApiError('NotFound', `No window ${o.window}`);
                const f = win.get_frame_rect();
                [x, y, w, h] = [f.x, f.y, f.width, f.height];
            }
            // Clamp to the stage.
            const x2 = Math.min(sw, x + w), y2 = Math.min(sh, y + h);
            x = Math.max(0, x); y = Math.max(0, y); w = x2 - x; h = y2 - y;
            if (w <= 0 || h <= 0)
                throw new ApiError('InvalidArgs', 'Empty area');

            // At most SHOTS_PER_SECOND per connection.
            const now = GLib.get_monotonic_time();
            c.shots = c.shots.filter(t => now - t < 1e6);
            if (c.shots.length >= SHOTS_PER_SECOND)
                throw new ApiError('RateLimited', `At most ${SHOTS_PER_SECOND} screenshots per second`);
            c.shots.push(now);

            if (o.hide_floating ?? true) {
                actors = [...this._floating].map(win => win.get_compositor_private()).filter(Boolean);
                saved = actors.map(a => a.opacity);
                actors.forEach(a => (a.opacity = 0));
            }
            const shooter = new Shell.Screenshot();
            const [content, scale, cursorContent, cursorPoint, cursorScale] =
                await shooter.screenshot_stage_to_content();
            actors.forEach((a, i) => (a.opacity = saved[i]));
            actors = [];
            this._blinkIndicator();

            const name = `drakter-${GLib.get_real_time()}-${GLib.random_int_range(0, 1e6)}.png`;
            file = Gio.File.new_for_path(GLib.build_filenamev([dir, name]));
            const stream = file.create(Gio.FileCreateFlags.PRIVATE, null);
            const cursorTex = o.cursor && cursorContent ? cursorContent.get_texture() : null;
            await Shell.Screenshot.composite_to_stream(content.get_texture(),
                x * scale, y * scale, w * scale, h * scale, scale,
                cursorTex, (cursorPoint?.x ?? 0) * scale, (cursorPoint?.y ?? 0) * scale, cursorScale ?? 1,
                stream);
            stream.close(null);
            invocation.return_value(new GLib.Variant('(s(iiii)d)', [file.get_path(), [x, y, w, h], scale]));
        } catch (e) {
            actors.forEach((a, i) => (a.opacity = saved[i]));
            try {
                file?.delete(null);
            } catch {}
            returnError(invocation, e instanceof ApiError ? e : new ApiError('Failed', `Screenshot failed: ${e.message}`));
        }
    }

    SetFloatingWindowAsync([match], invocation) {
        const sender = invocation.get_sender();
        if (!this._authed(invocation))
            return;
        try {
            this._checkOwner(sender);
            const m = unpackDict(match);
            const types = {wm_class: 'string', title: 'string', pid: 'int', monitor: 'int', cover: 'boolean'};
            for (const [k, val] of Object.entries(m)) {
                const t = types[k];
                if (!t)
                    throw new ApiError('InvalidArgs', `Unknown key ${k}`);
                if (t === 'int' ? !isInt(val) : typeof val !== t)
                    throw new ApiError('InvalidArgs', `${k} has the wrong type`);
            }
            const keys = Object.keys(m);
            if (keys.length && !keys.some(k => ['wm_class', 'title', 'pid'].includes(k)))
                throw new ApiError('InvalidArgs', 'Give at least one of wm_class, title or pid');
            const monitor = m.monitor ?? -1;
            if (monitor < -1 || monitor >= global.display.get_n_monitors())
                throw new ApiError('NotFound', `No monitor ${monitor}`);

            const rule = {owner: sender, monitor, cover: m.cover ?? true, match: {}};
            for (const k of ['wm_class', 'title', 'pid']) {
                if (m[k] !== undefined)
                    rule.match[k] = m[k];
            }
            if (keys.length && this._floatRule &&
                JSON.stringify(this._floatRule.match) === JSON.stringify(rule.match)) {
                // Same window (e.g. a monitor change): update the placement in
                // place. Releasing it would let mutter shrink it to the work area,
                // and a compositor resize cannot grow it back past that.
                this._floatRule.monitor = rule.monitor;
                this._floatRule.cover = rule.cover;
                for (const w of this._floating)
                    this._placeFloating(w);
            } else {
                this._releaseFloating();
            }
            if (keys.length && this._floatRule === null) {
                this._floatRule = rule;
                this._inputMode = 'none'; // until the first SetInputRegion
                this._inputRects = [];
                for (const w of global.display.list_all_windows())
                    this._maybeFloat(w);
            }
            invocation.return_value(new GLib.Variant('(b)', [this._floating.size > 0]));
        } catch (e) {
            returnError(invocation, e);
        }
    }

    SetInputRegionAsync([mode, rects], invocation) {
        if (!this._authed(invocation))
            return;
        try {
            this._checkOwner(invocation.get_sender());
            if (!['all', 'none', 'rects'].includes(mode))
                throw new ApiError('InvalidArgs', 'mode must be all|none|rects');
            if (rects.length > MAX_RECTS)
                throw new ApiError('InvalidArgs', `At most ${MAX_RECTS} rects`);
            this._inputMode = mode;
            this._inputRects = mode === 'rects' ? rects : [];
            this._updateInputRegion(true);
            const w = [...this._floating][0];
            const applied = !w ? 'pending' : w.get_client_type() === Meta.WindowClientType.WAYLAND ? 'compositor' : 'client';
            invocation.return_value(new GLib.Variant('(s)', [applied]));
        } catch (e) {
            returnError(invocation, e);
        }
    }

    SetEscapeGrabAsync([enabled], invocation) {
        if (!this._authed(invocation))
            return;
        this._setEscape(invocation.get_sender(), enabled);
        invocation.return_value(null);
    }

    SetFloatingFocusAsync([on], invocation) {
        if (!this._authed(invocation))
            return;
        try {
            this._checkOwner(invocation.get_sender());
            const w = [...this._floating][0];
            let ok;
            if (on) {
                ok = !!w;
                if (w) {
                    this._floatFocusOn = true;
                    w.activate(global.display.get_current_time_roundtrip());
                }
            } else {
                this._floatFocusOn = false;
                const f = global.display.get_focus_window();
                ok = f && this._floating.has(f) ? this._returnFocus() : true;
            }
            invocation.return_value(new GLib.Variant('(b)', [ok]));
        } catch (e) {
            returnError(invocation, e);
        }
    }

    ActivateWindowAsync([id], invocation) {
        if (!this._authed(invocation))
            return;
        const w = this._findWindow(id);
        const ok = !!w && !this._floating.has(w) && !w.is_override_redirect();
        if (ok)
            Main.activateWindow(w, global.display.get_current_time_roundtrip());
        invocation.return_value(new GLib.Variant('(b)', [ok]));
    }

    ForcePassthroughAsync([on], invocation) {
        const c = this._authed(invocation);
        if (!c)
            return;
        c.passthrough = !!on;
        this._updateInputRegion(true);
        invocation.return_value(null);
    }

    // ---------- signals ----------

    _broadcast(kind, name, params) {
        for (const [sender, c] of this._clients) {
            if (c.opts?.[kind])
                Gio.DBus.session.emit_signal(sender, OBJ_PATH, IFACE, name, params);
        }
    }

    // Shortcuts go to every connection subscribed with gestures or windows
    // (main subscribes with windows only from startup, CONTRACT §4.2).
    _emitShortcut(name, phase) {
        const params = new GLib.Variant('(ssx)', [name, phase, GLib.get_monotonic_time()]);
        for (const [sender, c] of this._clients) {
            if (c.opts?.gestures || c.opts?.windows)
                Gio.DBus.session.emit_signal(sender, OBJ_PATH, IFACE, 'Shortcut', params);
        }
    }

    _onPointerMoved() {
        this._updateInputRegion(false);
        const now = GLib.get_monotonic_time();
        for (const [sender, c] of this._clients) {
            if (!c.opts?.pointer)
                continue;
            const wait = c.lastPointer + c.opts.pointerMinUs - now;
            if (wait <= 0) {
                this._emitPointer(sender, c);
            } else if (!c.pending) {
                // Trailing emission so the last position is never lost.
                c.pending = this._timeout(Math.ceil(wait / 1000), () => {
                    c.pending = 0;
                    if (this._clients.get(sender) === c)
                        this._emitPointer(sender, c);
                });
            }
        }
    }

    _emitPointer(sender, c) {
        const [x, y, mods] = global.get_pointer();
        c.lastPointer = GLib.get_monotonic_time();
        Gio.DBus.session.emit_signal(sender, OBJ_PATH, IFACE, 'PointerMoved',
            new GLib.Variant('(iiux)', [x, y, mods, c.lastPointer]));
    }

    _windowsChanged(reason) {
        if (reason === 'restacked' || reason === 'geometry') {
            // Coalesce bursts (a drag emits dozens per second).
            if (this._wcPending?.has(reason))
                return;
            this._wcPending ??= new Set();
            this._wcPending.add(reason);
            this._timeout(30, () => {
                this._wcPending.delete(reason);
                this._broadcast('windows', 'WindowsChanged', new GLib.Variant('(s)', [reason]));
            });
            return;
        }
        this._broadcast('windows', 'WindowsChanged', new GLib.Variant('(s)', [reason]));
    }

    _onFocusChanged() {
        const w = global.display.get_focus_window();
        if (w && this._floating.has(w)) {
            if (!this._floatFocusOn) {
                // The floating window must not steal the focus: give it back
                // before the next frame and do not announce it.
                this._scheduleFocusReturn();
                return;
            }
        } else if (w) {
            this._prevFocus = w;
        }
        this._focusWin?.disconnectObject(this);
        this._focusWin = w;
        this._focusWin?.connectObject(
            'position-changed', () => this._windowsChanged('geometry'),
            'size-changed', () => this._windowsChanged('geometry'),
            'notify::title', () => this._broadcast('windows', 'FocusChanged',
                new GLib.Variant('(a{sv})', [this._winInfo(this._focusWin)])),
            this);
        this._broadcast('windows', 'FocusChanged',
            new GLib.Variant('(a{sv})', [this._focusWin ? this._winInfo(this._focusWin) : {}]));
    }

    _onWindowCreated(w) {
        this._windowsChanged('created');
        w.connectObject('unmanaged', () => {
            w.disconnectObject(this);
            if (this._prevFocus === w)
                this._prevFocus = null;
            if (this._floating.delete(w))
                this._emitFloating();
            this._windowsChanged('closed');
        }, this);
        if (!this._maybeFloat(w)) {
            // wm_class/title may arrive after creation (Wayland: set_app_id/set_title).
            w.connectObject('shown', () => this._laters.add(Meta.LaterType.BEFORE_REDRAW, () => {
                if (this._floatRule)
                    this._maybeFloat(w);
                return GLib.SOURCE_REMOVE;
            }),
                'notify::title', () => this._maybeFloat(w),
                'notify::wm-class', () => this._maybeFloat(w), this);
        }
    }

    _winInfo(w, stack = -1) {
        const app = Shell.WindowTracker.get_default().get_window_app(w);
        const ws = w.get_workspace();
        return {
            id: v.t(w.get_id()),
            wm_class: v.s(w.get_wm_class()),
            wm_class_instance: v.s(w.get_wm_class_instance()),
            app_id: v.s(app?.get_id()),
            gtk_app_id: v.s(w.get_gtk_application_id()),
            sandboxed_app_id: v.s(w.get_sandboxed_app_id()),
            title: v.s(w.get_title()),
            pid: v.i(w.get_pid()),
            client: v.s(w.get_client_type() === Meta.WindowClientType.WAYLAND ? 'wayland' : 'x11'),
            frame: v.rect(w.get_frame_rect()),
            buffer: v.rect(w.get_buffer_rect()),
            monitor: v.i(w.get_monitor()),
            workspace: v.i(w.is_on_all_workspaces() || !ws ? -1 : ws.index()),
            stack: v.i(stack),
            focused: v.b(w.has_focus()),
            minimized: v.b(w.minimized),
            fullscreen: v.b(w.fullscreen),
            maximized: v.b(w.maximized_horizontally && w.maximized_vertically),
            above: v.b(w.is_above()),
            sticky: v.b(w.is_on_all_workspaces()),
            type: v.s(Object.keys(Meta.WindowType).find(k => Meta.WindowType[k] === w.get_window_type())),
            floating: v.b(this._floating.has(w)),
        };
    }

    _visibleWindows() {
        const ws = global.workspace_manager.get_active_workspace();
        return global.display.sort_windows_by_stacking(global.display.list_all_windows())
            .filter(w => !w.minimized && !w.is_override_redirect() &&
                (w.is_on_all_workspaces() || w.get_workspace() === ws) &&
                w.get_compositor_private()?.visible)
            .reverse();
    }

    _findWindow(id) {
        const n = Number(id);
        return global.display.list_all_windows().find(w => w.get_id() === n) ?? null;
    }

    // ---------- focus (the floating window never steals it) ----------

    _scheduleFocusReturn() {
        if (this._focusLater)
            return;
        this._focusLater = this._laters.add(Meta.LaterType.BEFORE_REDRAW, () => {
            this._focusLater = 0;
            const f = global.display.get_focus_window();
            if (f && this._floating.has(f) && !this._floatFocusOn)
                this._returnFocus();
            return GLib.SOURCE_REMOVE;
        });
    }

    // Gives the focus back to the window that had it before the floating
    // window (or the topmost other window). Returns true if some window got it.
    _returnFocus() {
        const t = global.display.get_current_time_roundtrip();
        const alive = w => w && !this._floating.has(w) && !w.minimized &&
            global.display.list_all_windows().includes(w);
        let target = alive(this._prevFocus) ? this._prevFocus : null;
        target ??= this._visibleWindows().find(w => !this._floating.has(w) &&
            w.get_window_type() === Meta.WindowType.NORMAL) ?? null;
        if (target) {
            target.activate(t);
            return true;
        }
        global.display.unset_input_focus(t);
        return false;
    }

    // ---------- floating window ----------

    _matches(w) {
        const m = this._floatRule?.match;
        if (!m || w.is_override_redirect())
            return false;
        if (m.wm_class !== undefined && m.wm_class !== w.get_wm_class() &&
            m.wm_class !== w.get_wm_class_instance())
            return false;
        if (m.title !== undefined && m.title !== w.get_title())
            return false;
        if (m.pid !== undefined && m.pid !== w.get_pid())
            return false;
        return true;
    }

    _maybeFloat(w) {
        if (this._floating.has(w) || !this._matches(w))
            return this._floating.has(w);
        // Wait until the window is mapped ('shown' calls us again): touching a
        // window that is still being set up (stacking, skip-taskbar notify,
        // focus) races the shell's app tracker.
        if (!w.minimized && !w.get_compositor_private()?.visible)
            return false;
        this._patchWindowChain(w);
        this._floating.add(w);
        w.make_above();
        w.stick();
        // NEVER w.notify('skip-taskbar') here: ShellApp (C) counts its
        // "interesting" windows on every notify::skip-taskbar, assuming the
        // value really changed. A fake notify (the C value does not change)
        // corrupts the count; when the window closes the app stays RUNNING
        // with no running_state and gnome-shell 50.1 segfaults in
        // shell_app_compare() <- shell_window_tracker_get_app_from_pid().
        // Cost: an overview that is already open keeps showing the window
        // until it is reopened.
        this._placeFloating(w);
        // The first map may override the placement: apply it again then.
        w._drakterShownId = w.connect('shown', () => this._placeFloating(w));
        this._updateInputRegion(true);
        if (w.has_focus() && !this._floatFocusOn)
            this._scheduleFocusReturn();
        this._emitFloating();
        return true;
    }

    // cover: frame = geometry of the monitor with 1 px less height (so that
    // mutter does not take it for a fullscreen window).
    _placeFloating(w) {
        const r = this._floatRule;
        if (!r?.cover || !this._floating.has(w))
            return;
        let idx = r.monitor;
        if (idx < 0 || idx >= global.display.get_n_monitors())
            idx = global.display.get_current_monitor();
        const g = global.display.get_monitor_geometry(idx);
        // A monitor-sized window gets auto-maximized when it maps, and a
        // maximized window stays in the normal layer even with make_above.
        const wasMax = w.maximized_horizontally || w.maximized_vertically;
        if (w.fullscreen)
            w.unmake_fullscreen();
        if (wasMax)
            w.unmaximize();
        // user_op=true: a non-user move is constrained to the work area (below
        // the top bar); the floating window must cover the whole monitor. The
        // size only grows past the work area if the client asked for it (Electron
        // creates the window at the monitor size, CONTRACT §4.1).
        w.move_resize_frame(true, g.x, g.y, g.width, g.height - 1);
        if (wasMax && w.is_above()) {
            w.unmake_above(); // recompute the stack layer
            w.make_above();
        }
    }

    _releaseFloating() {
        for (const w of this._floating) {
            try {
                if (w._drakterShownId)
                    w.disconnect(w._drakterShownId);
                delete w._drakterShownId;
                w.unmake_above();
                w.unstick(); // no notify('skip-taskbar'): see _maybeFloat
            } catch {}
        }
        for (const [actor, reactive] of this._reactiveSaved) {
            try {
                actor.reactive = reactive;
            } catch {}
        }
        for (const w of this._floating) {
            const root = w.get_compositor_private();
            if (root)
                root._drakterHot = undefined; // re-apply the region if it floats again
        }
        this._reactiveSaved.clear();
        const had = this._floating.size > 0;
        this._floating.clear();
        this._floatRule = null;
        this._floatFocusOn = false;
        this._inputMode = 'none';
        this._inputRects = [];
        if (had)
            this._emitFloating();
    }

    _emitFloating() {
        const w = [...this._floating][0];
        this._broadcast('windows', 'FloatingWindowChanged',
            new GLib.Variant('(ba{sv})', [!!w, w ? this._winInfo(w) : {}]));
    }

    // GNOME has no API to set skip-taskbar on a Wayland toplevel. The JS side
    // of the shell (alt-tab, overview, app menu, dash-to-dock) reads
    // MetaWindow.skip_taskbar, so we answer true for the floating window there.
    _patchSkipTaskbar() {
        this._patchedProtos = new Map(); // proto -> {skip, skipCamel, isSkip}
        this._patchProto(Meta.Window.prototype);
    }

    // GJS resolves GObject properties lazily and may define them on the
    // prototype of the concrete (private) subclass, e.g. MetaWindowWayland,
    // so every prototype of the chain of a floating window is patched.
    _patchWindowChain(w) {
        for (let p = Object.getPrototypeOf(w); p && p !== Object.prototype; p = Object.getPrototypeOf(p))
            this._patchProto(p);
    }

    _patchProto(proto) {
        if (this._patchedProtos.has(proto))
            return;
        const own = n => Object.getOwnPropertyDescriptor(proto, n);
        this._patchedProtos.set(proto, {skip: own('skip_taskbar'), camel: own('skipTaskbar'),
            isSkip: own('is_skip_taskbar')});
        const floating = this._floating;
        const realIs = this._origIsSkip;
        const desc = {
            configurable: true,
            get() {
                return floating.has(this) || realIs.call(this);
            },
        };
        Object.defineProperty(proto, 'skip_taskbar', desc);
        Object.defineProperty(proto, 'skipTaskbar', desc);
        const isSkip = function () {
            return floating.has(this) || realIs.call(this);
        };
        const d = own('is_skip_taskbar');
        if (d && !d.configurable)
            proto.is_skip_taskbar = isSkip; // GI methods: writable, not configurable
        else
            Object.defineProperty(proto, 'is_skip_taskbar', {configurable: true, writable: true, value: isSkip});
    }

    _unpatchSkipTaskbar() {
        for (const [proto, saved] of this._patchedProtos) {
            for (const [name, d] of [['skip_taskbar', saved.skip], ['skipTaskbar', saved.camel], ['is_skip_taskbar', saved.isSkip]]) {
                if (d && !d.configurable) {
                    proto[name] = d.value;
                    continue;
                }
                delete proto[name];
                if (d)
                    Object.defineProperty(proto, name, d);
            }
        }
        this._patchedProtos.clear();
    }

    // Input region: mutter decides which surface gets a pointer event by
    // picking Clutter actors, and only reactive actors are picked. Making the
    // floating window's surface actors non-reactive lets the event fall
    // through to the window below. We flip that per pointer position against
    // the app's hot rects (the model Roamies uses on macOS/Windows with
    // set_ignore_cursor_events). ForcePassthrough wins over the rects.
    _updateInputRegion(force) {
        if (!this._floating.size)
            return;
        const [px, py, mods] = global.get_pointer();
        if (!force && (mods & ANY_BUTTON))
            return; // never change targets in the middle of a press/drag
        const passthrough = [...this._clients.values()].some(c => c.passthrough);
        for (const w of this._floating) {
            // XWayland: the X server routes pointer events by its own stacking and
            // X11 input shape, so flipping the compositor pick would only desync
            // focus. The app sets the X11 input shape (see SetInputRegion doc).
            if (w.get_client_type() !== Meta.WindowClientType.WAYLAND)
                continue;
            let hot = true;
            if (passthrough || this._inputMode === 'none') {
                hot = false;
            } else if (this._inputMode === 'rects') {
                const f = w.get_frame_rect();
                const rx = px - f.x, ry = py - f.y;
                hot = this._inputRects.some(([x, y, rw, rh]) =>
                    rx >= x && ry >= y && rx < x + rw && ry < y + rh);
            }
            this._setWindowReactive(w, hot);
        }
    }

    _setWindowReactive(w, reactive) {
        const root = w.get_compositor_private();
        if (!root || root._drakterHot === reactive)
            return;
        root._drakterHot = reactive;
        const walk = actor => {
            for (const child of actor.get_children()) {
                if (!this._reactiveSaved.has(child))
                    this._reactiveSaved.set(child, child.reactive);
                child.reactive = reactive && this._reactiveSaved.get(child);
                walk(child);
            }
        };
        walk(root);
        // Clutter picks from a stack recorded while painting: without a redraw
        // the old reactive state would keep being used.
        root.queue_redraw();
        root.queue_relayout(); // makes Clutter repick input devices (drops its pick cache)
        if (!root._drakterWatched) {
            root._drakterWatched = true;
            // New surface actors can be attached later (buffer/role changes).
            for (const a of [root, ...root.get_children()]) {
                a.connectObject('child-added', () => {
                    root._drakterHot = undefined;
                    this._updateInputRegion(true);
                }, this);
            }
        }
    }

    // ---------- shortcuts ----------

    _grab(accel, name, flags = Meta.KeyBindingFlags.NONE) {
        const action = global.display.grab_accelerator(accel, flags);
        if (action === Meta.KeyBindingAction.NONE) {
            console.warn(`drakter-companion: cannot grab ${accel}`);
            return 0;
        }
        Main.wm.allowKeybinding(Meta.external_binding_name_for_action(action), SHORTCUT_MODES);
        this._accels.set(action, name);
        return action;
    }

    _ungrab(action) {
        global.display.ungrab_accelerator(action);
        Main.wm.allowKeybinding(Meta.external_binding_name_for_action(action), Shell.ActionMode.NONE);
        this._accels.delete(action);
    }

    _grabPushToTalk() {
        if (this._pttAction)
            this._ungrab(this._pttAction);
        const accel = this._settings.get_string('push-to-talk');
        this._pttAction = accel ? this._grab(accel, 'push-to-talk', Meta.KeyBindingFlags.TRIGGER_RELEASE) : 0;
    }

    _setEscape(sender, enabled) {
        const c = this._clients.get(sender);
        if (c)
            c.escape = enabled;
        const want = [...this._clients.values()].some(x => x.escape);
        if (want && !this._escAction)
            this._escAction = this._grab('Escape', 'escape');
        else if (!want && this._escAction) {
            this._ungrab(this._escAction);
            this._escAction = 0;
        }
    }

    _onAccelerator(action, phase) {
        const name = this._accels.get(action);
        if (name && !(name === 'escape' && phase === 'release'))
            this._emitShortcut(name, phase);
    }

    // ---------- buttons (polled) + modifier gestures (event-driven) ----------

    // Mouse buttons on other apps produce no shell-visible event on Wayland,
    // so they are polled, and only while a client asked for them (Roamies
    // does the same: it reads the left button only during INK_WAIT).
    _syncPoll() {
        const need = [...this._clients.values()].some(c => c.opts?.buttons);
        if (need && this._pollId)
            return;
        this._stopPoll();
        if (need) {
            const ms = Math.max(4, this._settings.get_uint('poll-ms'));
            this._prevButtons = global.get_pointer()[2] & ANY_BUTTON;
            this._pollId = GLib.timeout_add(GLib.PRIORITY_HIGH, ms, () => {
                this._pollButtons();
                return GLib.SOURCE_CONTINUE;
            });
        }
    }

    _stopPoll() {
        if (this._pollId)
            GLib.source_remove(this._pollId);
        this._pollId = 0;
    }

    _pollButtons() {
        const [x, y, mods] = global.get_pointer();
        const buttons = mods & ANY_BUTTON;
        if (buttons === this._prevButtons)
            return;
        const now = GLib.get_monotonic_time();
        for (const [btn, mask] of BUTTON_MASKS) {
            if ((buttons ^ this._prevButtons) & mask) {
                this._broadcast('buttons', 'Button',
                    new GLib.Variant('(ubiix)', [btn, !!(buttons & mask), x, y, now]));
            }
        }
        this._prevButtons = buttons;
    }

    // Modifier changes come from ClutterKeymap::state-changed (no polling);
    // timers re-run the state machine for the hold threshold and the release
    // debounce. Non-modifier keys are invisible to the shell while a client
    // has keyboard focus, so "another key spoils the gesture" is not possible:
    // that is why modifier-gestures is off by default (CONTRACT §3.2).
    _gestureStep() {
        if (!this._settings.get_boolean('modifier-gestures') ||
            ![...this._clients.values()].some(c => c.opts?.gestures))
            return;
        const mods = global.get_pointer()[2];
        const now = GLib.get_monotonic_time();
        const g = this._gesture;
        const prev = g.prevMods;
        g.prevMods = mods;

        const ctrl = !!(mods & M.CONTROL_MASK), alt = !!(mods & M.MOD1_MASK);
        const shift = !!(mods & M.SHIFT_MASK), sup = !!(mods & SUPER), btn = !!(mods & ANY_BUTTON);
        const holdMs = this._settings.get_uint('hold-ms');
        const tapUs = this._settings.get_uint('tap-max-ms') * 1000;
        const emit = (name, phase) => this._broadcast('gestures', 'Gesture',
            new GLib.Variant('(ssx)', [name, phase, now]));
        const recheck = ms => this._timeout(ms, () => this._gestureStep());

        // Talk: hold Ctrl+Alt.
        switch (g.talk) {
        case 'idle':
            if (ctrl && alt && !shift && !sup && !btn && !((prev & M.CONTROL_MASK) && (prev & M.MOD1_MASK))) {
                g.talk = 'armed';
                g.talkSince = now;
                emit('talk', 'armed');
                recheck(holdMs);
            }
            break;
        case 'armed':
            if (shift || sup || btn) {
                g.talk = 'spoiled';
                emit('talk', 'cancel');
            } else if (!ctrl || !alt) {
                g.talk = 'idle';
                emit('talk', 'tap');
            } else if (now - g.talkSince >= holdMs * 1000 - 1000) {
                g.talk = 'holding';
                g.releasedSince = 0;
                emit('talk', 'hold');
            }
            break;
        case 'holding':
            if (shift || sup) {
                g.talk = 'spoiled';
                emit('talk', 'cancel');
            } else if (!ctrl || !alt) {
                if (!g.releasedSince) {
                    g.releasedSince = now;
                    recheck(90); // release debounce
                } else if (now - g.releasedSince >= 89000) {
                    g.talk = 'idle';
                    emit('talk', 'release');
                }
            } else {
                g.releasedSince = 0;
            }
            break;
        case 'spoiled':
            if (!ctrl && !alt)
                g.talk = 'idle';
            break;
        }

        // Ask: tap Ctrl+Shift.
        switch (g.ask) {
        case 'idle':
            if (ctrl && shift && !alt && !sup && !btn) {
                g.ask = 'pressing';
                g.askSince = now;
            }
            break;
        case 'pressing':
            if (alt || sup || btn || now - g.askSince > tapUs) {
                g.ask = 'spoiled';
            } else if (!ctrl && !shift) {
                g.ask = 'idle';
                emit('ask', 'tap');
            }
            break;
        case 'spoiled':
            if (!ctrl && !shift)
                g.ask = 'idle';
            break;
        }
    }

    // ---------- helpers ----------

    _checkDir(dir) {
        if (typeof dir !== 'string' || !GLib.path_is_absolute(dir))
            throw new ApiError('InvalidArgs', 'dir must be an absolute path');
        const canon = GLib.canonicalize_filename(dir, null);
        const roots = [GLib.get_user_runtime_dir(), GLib.get_home_dir()];
        if (!roots.some(r => canon === r || canon.startsWith(`${r}/`)))
            throw new ApiError('InvalidArgs', 'dir must be under $XDG_RUNTIME_DIR or $HOME');
        let info;
        try {
            info = Gio.File.new_for_path(canon).query_info(
                'standard::type,standard::is-symlink,unix::uid,unix::mode',
                Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, null);
        } catch (e) {
            throw new ApiError('InvalidArgs', `dir is not usable (${e.message})`);
        }
        if (info.get_is_symlink() || info.get_file_type() !== Gio.FileType.DIRECTORY)
            throw new ApiError('InvalidArgs', 'dir must be a real directory');
        if (info.get_attribute_uint32('unix::uid') !== this._uid)
            throw new ApiError('InvalidArgs', 'dir must belong to this user');
        if (info.get_attribute_uint32('unix::mode') & 0o022)
            throw new ApiError('InvalidArgs', 'dir must not be group/world writable');
        return canon;
    }

    _timeout(ms, fn) {
        const id = GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => {
            this._timeouts.delete(id);
            fn();
            return GLib.SOURCE_REMOVE;
        });
        this._timeouts.add(id);
        return id;
    }
}

// Only exported with DRAKTER_COMPANION_DEBUG=1 in the gnome-shell environment
// (used by the headless test, never in a normal session). Injects input
// through a Clutter virtual device and reports internal state.
class DebugApi {
    constructor(ext) {
        this._ext = ext;
        const seat = global.stage.context.get_backend().get_default_seat();
        this._ptr = seat.create_virtual_device(Clutter.InputDeviceType.POINTER_DEVICE);
        this._kbd = seat.create_virtual_device(Clutter.InputDeviceType.KEYBOARD_DEVICE);
    }

    InjectAsync([kind, x, y, code], invocation) {
        if (!this._ext._authed(invocation))
            return;
        const t = GLib.get_monotonic_time();
        const P = Clutter.ButtonState.PRESSED, R = Clutter.ButtonState.RELEASED;
        switch (kind) {
        case 'motion': this._ptr.notify_absolute_motion(t, x, y); break;
        case 'press': this._ptr.notify_button(t, code, P); break;
        case 'release': this._ptr.notify_button(t, code, R); break;
        case 'keydown': this._kbd.notify_keyval(t, code, Clutter.KeyState.PRESSED); break;
        case 'keyup': this._kbd.notify_keyval(t, code, Clutter.KeyState.RELEASED); break;
        default: returnError(invocation, new ApiError('InvalidArgs', 'bad kind')); return;
        }
        invocation.return_value(null);
    }

    ProbeAsync(_p, invocation) {
        if (!this._ext._authed(invocation))
            return;
        const e = this._ext;
        const w = [...e._floating][0];
        const info = {
            stage_key_events: v.u(e._stageKeyEvents),
            floating: v.b(!!w),
            poll_active: v.b(!!e._pollId),
            keymap_changes: v.u(e._keymapChanges),
            display: v.s(GLib.getenv('DISPLAY')),
            xauthority: v.s(GLib.getenv('XAUTHORITY')),
            indicator: v.b(!!e._indicator?.visible),
            blinks: v.u(e._blinks),
            float_focus_on: v.b(e._floatFocusOn),
            passthrough: v.b([...e._clients.values()].some(c => c.passthrough)),
        };
        const [px, py] = global.get_pointer();
        const picked = global.stage.get_actor_at_pos(Clutter.PickMode.REACTIVE, px, py);
        const chain = [];
        for (let a = picked; a; a = a.get_parent())
            chain.push(a.constructor.$gtype.name);
        info.picked = v.s(`${px},${py}: ${chain.slice(0, 3).join(' < ')}`);
        if (w) {
            const root = w.get_compositor_private();
            info.js_skip_taskbar = v.b(w.skip_taskbar);
            info.c_skip_taskbar = v.b(e._origIsSkip.call(w));
            info.above = v.b(w.is_above());
            info.sticky = v.b(w.is_on_all_workspaces());
            info.hot = v.b(root?._drakterHot ?? true);
            info.actor_tree = v.s(JSON.stringify(dump(root)));
        }
        invocation.return_value(new GLib.Variant('(a{sv})', [info]));
    }
}

function dump(actor) {
    return actor ? {t: actor.constructor.$gtype.name, r: actor.reactive, c: actor.get_children().map(dump)} : null;
}
