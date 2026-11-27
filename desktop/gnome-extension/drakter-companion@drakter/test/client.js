// End-to-end check of drakter-companion (API v2) inside the private headless shell.
// usage (inside run-headless.sh): gjs -m client.js <ROOT> <HERE> <SCHEMADIR>
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GdkPixbuf from 'gi://GdkPixbuf';
import System from 'system';
Gio._promisify(Gio.DBusConnection.prototype, 'call');

const [ROOT, HERE, SCHEMADIR] = ARGV;
const NAME = 'org.drakter.Companion', PATH = '/org/drakter/Companion', IFACE = 'org.drakter.Companion1';
const ERR = 'org.drakter.Companion1.Error.';
const bus = Gio.DBus.session;
const results = [];
const ok = (name, cond, extra = '') => {
    results.push([name, !!cond]);
    print(`${cond ? 'PASS' : 'FAIL'}  ${name}${extra ? `  -- ${extra}` : ''}`);
};
const sleep = ms => new Promise(r => GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => (r(), GLib.SOURCE_REMOVE)));
const now = () => GLib.get_monotonic_time();

async function call(method, sig = null, args = [], iface = IFACE, conn = bus) {
    const reply = await conn.call(NAME, PATH, iface, method,
        sig ? new GLib.Variant(sig, args) : null, null, Gio.DBusCallFlags.NONE, 10000, null);
    return reply.recursiveUnpack();
}
// Returns the D-Bus error name of a failing call, or null if it succeeded.
async function errName(...a) {
    try {
        await call(...a);
        return null;
    } catch (e) {
        return Gio.DBusError.get_remote_error(e) ?? e.message;
    }
}
const dbg = (kind, x = 0, y = 0, code = 0) => call('Inject', '(siiu)', [kind, x, y, code], `${IFACE}.Debug`);
const probeNow = async () => (await call('Probe', null, [], `${IFACE}.Debug`))[0];
const B = x => new GLib.Variant('b', x);

// --- signal capture ---
const signals = [];
bus.signal_subscribe(null, IFACE, null, PATH, null, Gio.DBusSignalFlags.NONE,
    (_c, _sender, _path, _iface, name, params) => signals.push({name, args: params.recursiveUnpack(), t: now()}));
const waitSignal = async (pred, ms = 1500) => {
    const end = now() + ms * 1000;
    while (now() < end) {
        const s = signals.find(pred);
        if (s)
            return s;
        await sleep(2);
    }
    return null;
};

// --- GTK test windows ---
let X11_DISPLAY = null; // set when X11=1: test windows run through XWayland
function spawnWin(title, color, w, h) {
    const launcher = new Gio.SubprocessLauncher({flags: Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE});
    if (X11_DISPLAY) {
        launcher.setenv('GDK_BACKEND', 'x11', true);
        launcher.setenv('DISPLAY', X11_DISPLAY.display, true);
        launcher.setenv('XAUTHORITY', X11_DISPLAY.xauthority, true);
    }
    const proc = launcher.spawnv(['gjs', '-m', `${HERE}/gtkwin.js`, title, color, `${w}`, `${h}`]);
    const lines = [];
    const stream = new Gio.DataInputStream({base_stream: proc.get_stdout_pipe()});
    const read = () => stream.read_line_async(GLib.PRIORITY_DEFAULT, null, (s, res) => {
        const [line] = s.read_line_finish_utf8(res);
        if (line !== null) {
            lines.push(line);
            read();
        }
    });
    read();
    return {proc, lines};
}

async function clickAt(x, y) {
    await dbg('motion', x, y);
    await sleep(40);
    await dbg('motion', x + 1, y); // second motion: forces a repick after a reactive flip
    await sleep(40);
    await dbg('press', 0, 0, 1);
    await sleep(20);
    await dbg('release', 0, 0, 1);
    await sleep(150);
}
const clicked = win => win.lines.some(l => l.startsWith('CLICK'));
const activeTitle = async () => (await call('GetActiveWindow'))[0].title;

function pixel(path, x, y) {
    const pb = GdkPixbuf.Pixbuf.new_from_file(path);
    const px = pb.get_pixels(), o = y * pb.get_rowstride() + x * pb.get_n_channels();
    return {w: pb.get_width(), h: pb.get_height(), rgb: [px[o], px[o + 1], px[o + 2]]};
}

const pct = (arr, p) => [...arr].sort((a, b) => a - b)[Math.floor((arr.length - 1) * p)];
const ms = us => (us / 1000).toFixed(2);
const K = {ctrl: 0xffe3, alt: 0xffe9, shift: 0xffe1, sup: 0xffeb, d: 0x64, space: 0x20, esc: 0xff1b, a: 0x61};
const keys = async (...codes) => {
    for (const c of codes)
        await dbg('keydown', 0, 0, c);
    for (const c of [...codes].reverse())
        await dbg('keyup', 0, 0, c);
};

async function main() {
    // 1. Security: no Hello / bad token / good token; Version 2; named errors.
    const other = Gio.DBusConnection.new_for_address_sync(GLib.getenv('DBUS_SESSION_BUS_ADDRESS'),
        Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION, null, null);
    let e = await errName('GetPointer', null, [], IFACE, other);
    ok('GetPointer without Hello -> AccessDenied', e === `${ERR}AccessDenied`, e);
    e = await errName('Screenshot', '(a{sv})', [{dir: new GLib.Variant('s', `${ROOT}/rt`)}], IFACE, other);
    ok('Screenshot without Hello -> AccessDenied', e === `${ERR}AccessDenied`, e);
    e = await errName('ForcePassthrough', '(b)', [true], IFACE, other);
    ok('ForcePassthrough without Hello -> AccessDenied', e === `${ERR}AccessDenied`, e);
    e = await errName('Hello', '(s)', ['wrong'], IFACE, other);
    ok('Hello with a wrong token -> AccessDenied', e === `${ERR}AccessDenied`, e);
    e = await errName('GetPointer', null, [], IFACE, other);
    ok('still denied after a wrong token', e === `${ERR}AccessDenied`, e);
    const tokPath = `${ROOT}/rt/drakter-companion/token`;
    const mode = Gio.File.new_for_path(tokPath).query_info('unix::mode', 0, null).get_attribute_uint32('unix::mode') & 0o777;
    ok('token file is 0600', mode === 0o600, mode.toString(8));
    const token = new TextDecoder().decode(GLib.file_get_contents(tokPath)[1]);
    const [ver] = (await bus.call(NAME, PATH, 'org.freedesktop.DBus.Properties', 'Get',
        new GLib.Variant('(ss)', [IFACE, 'Version']), null, 0, -1, null)).recursiveUnpack();
    ok('property Version = 2', ver === 2, `${ver}`);
    const [info] = await call('Hello', '(s)', [token]);
    const need = ['pointer', 'buttons', 'gestures', 'windows', 'screenshot', 'input-region', 'focus', 'passthrough', 'activate'];
    ok('Hello: version 2 and capabilities', info.version === 2 && need.every(c => info.capabilities.includes(c)), JSON.stringify(info));
    let probe = await probeNow();
    ok('panel indicator visible with an authenticated client', probe.indicator);

    // 2. Pointer polling cost.
    await dbg('motion', 10, 10); // first absolute event of a new virtual device
    await sleep(50);
    await dbg('motion', 300, 200);
    await sleep(50);
    await call('GetPointer');
    await dbg('motion', 300, 200); // the first absolute sample of a new virtual device has an axis at 0
    await sleep(50);
    const lat = [];
    let p;
    for (let i = 0; i < 300; i++) {
        const t0 = now();
        p = await call('GetPointer');
        lat.push(now() - t0);
    }
    ok('GetPointer returns injected position', p[0] === 300 && p[1] === 200, JSON.stringify(p));
    print(`  GetPointer round trip: p50 ${ms(pct(lat, 0.5))} ms, p95 ${ms(pct(lat, 0.95))} ms, max ${ms(Math.max(...lat))} ms`);
    const [mons] = await call('GetMonitors');
    ok('GetMonitors', mons.length === 1 && mons[0].geometry[2] === 1280, JSON.stringify(mons));

    // 3. Windows and the floating window.
    if (GLib.getenv('X11') !== null && GLib.getenv('X11') !== '') {
        X11_DISPLAY = await probeNow();
        print(`  X11 mode: test windows on XWayland DISPLAY=${X11_DISPLAY.display}`);
    }
    const target = spawnWin('target', '#0000ff', 1100, 700);
    await sleep(1500);
    const floatW = spawnWin('drakter-floating', '#ff0000', 1280, 799);
    await sleep(1500);
    ok('GTK test windows ready', target.lines.includes('READY target') && floatW.lines.includes('READY drakter-floating'));

    await call('Subscribe', '(a{sv})', [{
        pointer: B(true), pointer_min_ms: new GLib.Variant('u', 8),
        buttons: B(true), gestures: B(true), windows: B(true),
    }]);

    ok('GetActiveWindow (before the rule, the new window has the focus)', await activeTitle() === 'drakter-floating');
    e = await errName('SetFloatingWindow', '(a{sv})', [{cover: B(true)}]);
    ok('SetFloatingWindow without a match key -> InvalidArgs', e === `${ERR}InvalidArgs`, e);
    e = await errName('SetFloatingWindow', '(a{sv})', [{title: new GLib.Variant('s', 'drakter-floating'), monitor: new GLib.Variant('i', 5)}]);
    ok('SetFloatingWindow on a missing monitor -> NotFound', e === `${ERR}NotFound`, e);
    signals.length = 0;
    const [found] = await call('SetFloatingWindow', '(a{sv})', [{
        title: new GLib.Variant('s', 'drakter-floating'), monitor: new GLib.Variant('i', -1)}]);
    ok('SetFloatingWindow found the window', found);
    await sleep(400);
    probe = await probeNow();
    ok('floating: above + sticky', probe.above && probe.sticky, JSON.stringify({above: probe.above, sticky: probe.sticky}));
    ok('floating: hidden from alt-tab/overview (JS skip_taskbar)', probe.js_skip_taskbar && !probe.c_skip_taskbar,
        `js=${probe.js_skip_taskbar} c=${probe.c_skip_taskbar}`);
    ok('floating gives the focus back to the previous window', await activeTitle() === 'target', await activeTitle());
    ok('no FocusChanged announces the floating window',
        !signals.some(s => s.name === 'FocusChanged' && s.args[0]?.title === 'drakter-floating'));

    // Main calls it again on a monitor change: the same rule is updated in place.
    await call('SetFloatingWindow', '(a{sv})', [{title: new GLib.Variant('s', 'drakter-floating'), monitor: new GLib.Variant('i', 0)}]);
    await sleep(400);
    let [wins] = await call('ListWindows');
    print(`  ListWindows: ${wins.map(w => `${w.title}[${w.client}] ${w.frame} stack=${w.stack}`).join(' | ')}`);
    ok('ListWindows top-to-bottom, floating first', wins[0]?.title === 'drakter-floating' && wins.some(w => w.title === 'target'));
    const flWin = wins.find(w => w.title === 'drakter-floating');
    const tgWin = wins.find(w => w.title === 'target');
    const fl = flWin.frame, tg = tgWin.frame;
    ok('cover: frame = monitor with 1 px less height (also after calling it again)', fl.join() === '0,0,1280,799', fl.join());

    // Owner check: another authenticated connection cannot drive the floating window.
    await call('Hello', '(s)', [token], IFACE, other);
    e = await errName('SetInputRegion', '(sa(iiii))', ['all', []], IFACE, other);
    ok('SetInputRegion from a non-owner -> AccessDenied', e === `${ERR}AccessDenied`, e);
    e = await errName('SetFloatingWindow', '(a{sv})', [{}], IFACE, other);
    ok('SetFloatingWindow from a non-owner -> AccessDenied', e === `${ERR}AccessDenied`, e);

    // 4. Pointer signal latency (inject -> signal received by this client).
    signals.length = 0;
    const plat = [];
    for (let i = 0; i < 60; i++) {
        const t0 = now();
        await dbg('motion', 100 + i * 3, 100);
        const s = await waitSignal(x => x.name === 'PointerMoved' && x.args[0] === 100 + i * 3, 500);
        if (s)
            plat.push(s.t - t0);
        await sleep(10);
    }
    ok('PointerMoved signals arrive', plat.length >= 55, `${plat.length}/60`);
    if (plat.length)
        print(`  inject->PointerMoved: p50 ${ms(pct(plat, 0.5))} ms, p95 ${ms(pct(plat, 0.95))} ms (includes the Inject call)`);

    // 5. Input region / click-through / ForcePassthrough.
    const inside = [fl[0] + 50, fl[1] + 50]; // hot rect: top-left 100x100 of the floating window
    const cold = [tg[0] + 200, tg[1] + 200];
    ok('cold point is over the target', cold[0] < tg[0] + tg[2] && cold[1] < tg[1] + tg[3]);
    if (!X11_DISPLAY) {
        floatW.lines.length = 0; target.lines.length = 0;
        await clickAt(...cold);
        ok('region "none" until the first SetInputRegion', clicked(target) && !clicked(floatW),
            `float=${floatW.lines} target=${target.lines}`);
        const [applied] = await call('SetInputRegion', '(sa(iiii))', ['rects', [[0, 0, 100, 100]]]);
        ok('SetInputRegion applied by the compositor', applied === 'compositor', applied);
        e = await errName('SetInputRegion', '(sa(iiii))', ['bogus', []]);
        ok('SetInputRegion bad mode -> InvalidArgs', e === `${ERR}InvalidArgs`, e);
        e = await errName('SetInputRegion', '(sa(iiii))', ['rects', Array.from({length: 257}, () => [0, 0, 1, 1])]);
        ok('SetInputRegion with 257 rects -> InvalidArgs', e === `${ERR}InvalidArgs`, e);
        floatW.lines.length = 0; target.lines.length = 0;
        signals.length = 0;
        await clickAt(...inside);
        ok('click on hot rect goes to the floating window', clicked(floatW) && !clicked(target),
            `float=${floatW.lines} target=${target.lines}`);
        const btn = await waitSignal(s => s.name === 'Button' && s.args[1] === true);
        ok('Button pressed signal', btn && btn.args[0] === 1, JSON.stringify(btn?.args));
        await sleep(100);
        ok('clicking the floating window does not steal the focus', await activeTitle() === 'target', await activeTitle());
        floatW.lines.length = 0; target.lines.length = 0;
        await clickAt(...cold);
        ok('click outside hot rects passes through to the window below', clicked(target) && !clicked(floatW),
            `float=${floatW.lines} target=${target.lines}`);
        ok('floating window still on top', (await call('ListWindows'))[0][0].title === 'drakter-floating');
        await call('SetInputRegion', '(sa(iiii))', ['all', []]);
        floatW.lines.length = 0; target.lines.length = 0;
        await clickAt(...cold);
        ok('mode "all": same point goes to the floating window', clicked(floatW) && !clicked(target));
        await call('ForcePassthrough', '(b)', [true]);
        floatW.lines.length = 0; target.lines.length = 0;
        await clickAt(...cold);
        ok('ForcePassthrough(true): the click passes through despite "all"', clicked(target) && !clicked(floatW),
            `float=${floatW.lines} target=${target.lines}`);
        await call('ForcePassthrough', '(b)', [false]);
        floatW.lines.length = 0; target.lines.length = 0;
        await clickAt(...cold);
        ok('ForcePassthrough(false): the floating window takes it again', clicked(floatW) && !clicked(target));
        await call('SetInputRegion', '(sa(iiii))', ['none', []]);
        floatW.lines.length = 0; target.lines.length = 0;
        await clickAt(...inside);
        ok('mode "none": hot point passes through', !clicked(floatW));
        // Static cursor, region changes under it (Roamies re-checks every 120 ms for this).
        await clickAt(...cold);
        await call('SetInputRegion', '(sa(iiii))', ['rects', [[0, 0, 1280, 799]]]);
        floatW.lines.length = 0; target.lines.length = 0;
        await dbg('press', 0, 0, 1); await sleep(20); await dbg('release', 0, 0, 1); await sleep(150);
        ok('region grown under a static cursor applies without motion', clicked(floatW),
            `float=${floatW.lines} target=${target.lines}`);
        await call('SetInputRegion', '(sa(iiii))', ['rects', [[0, 0, 100, 100]]]);
    }

    // 6. Focus: SetFloatingFocus and ActivateWindow.
    let [r] = await call('SetFloatingFocus', '(b)', [true]);
    await sleep(150);
    ok('SetFloatingFocus(true): the floating window gets the focus', r && await activeTitle() === 'drakter-floating', await activeTitle());
    floatW.lines.length = 0; target.lines.length = 0;
    await keys(K.a);
    await sleep(100);
    ok('  …and the keyboard', floatW.lines.some(l => l === 'KEY drakter-floating 97'), `float=${floatW.lines} target=${target.lines}`);
    [r] = await call('SetFloatingFocus', '(b)', [false]);
    await sleep(150);
    ok('SetFloatingFocus(false): the focus goes back to the previous window', r && await activeTitle() === 'target', await activeTitle());
    await call('SetFloatingFocus', '(b)', [true]);
    await sleep(150);
    [r] = await call('ActivateWindow', '(t)', [tgWin.id]);
    await sleep(150);
    ok('ActivateWindow(target) activates it', r && await activeTitle() === 'target', await activeTitle());
    [r] = await call('ActivateWindow', '(t)', [flWin.id]);
    ok('ActivateWindow(floating) -> false', r === false);
    [r] = await call('ActivateWindow', '(t)', [987654321]);
    ok('ActivateWindow(missing) -> false', r === false);
    await call('SetFloatingFocus', '(b)', [false]);

    // 7. Modifier gestures: off by default, then on.
    signals.length = 0;
    await dbg('keydown', 0, 0, K.ctrl); await dbg('keydown', 0, 0, K.alt);
    await sleep(400);
    await dbg('keyup', 0, 0, K.alt); await dbg('keyup', 0, 0, K.ctrl);
    await sleep(200);
    ok('modifier-gestures false by default: no Gesture', !signals.some(s => s.name === 'Gesture'));
    GLib.spawn_command_line_sync(`gsettings --schemadir ${SCHEMADIR} set org.gnome.shell.extensions.drakter-companion modifier-gestures true`);
    await sleep(300);
    signals.length = 0;
    await dbg('keydown', 0, 0, K.ctrl); await dbg('keydown', 0, 0, K.alt);
    await sleep(400);
    await dbg('keyup', 0, 0, K.alt); await dbg('keyup', 0, 0, K.ctrl);
    await sleep(200);
    const phases = signals.filter(s => s.name === 'Gesture' && s.args[0] === 'talk').map(s => s.args[1]);
    ok('modifier-gestures true: Ctrl+Alt hold -> armed, hold, release', phases.join() === 'armed,hold,release', phases.join());
    GLib.spawn_command_line_sync(`gsettings --schemadir ${SCHEMADIR} reset org.gnome.shell.extensions.drakter-companion modifier-gestures`);

    // 8. Shortcuts (a windows-only subscriber gets them too, CONTRACT §4.2).
    await call('Subscribe', '(a{sv})', [{windows: B(true)}]);
    signals.length = 0;
    await keys(K.sup, K.alt, K.d);
    await sleep(150);
    ok('Super+Alt+D -> Shortcut toggle-floating (windows-only subscriber)',
        signals.some(s => s.name === 'Shortcut' && s.args[0] === 'toggle-floating' && s.args[1] === 'press'));
    signals.length = 0;
    await keys(K.sup, K.alt, K.a);
    await sleep(150);
    ok('Super+Alt+A -> Shortcut ask/press', signals.some(s => s.name === 'Shortcut' && s.args[0] === 'ask' && s.args[1] === 'press'),
        signals.map(s => `${s.name}:${s.args}`).join(' '));
    signals.length = 0;
    await dbg('keydown', 0, 0, K.sup); await dbg('keydown', 0, 0, K.alt);
    await dbg('keydown', 0, 0, K.space); await sleep(300); await dbg('keyup', 0, 0, K.space);
    await dbg('keyup', 0, 0, K.alt); await dbg('keyup', 0, 0, K.sup);
    await sleep(150);
    const ptt = signals.filter(s => s.name === 'Shortcut' && s.args[0] === 'push-to-talk').map(s => s.args[1]);
    ok('Super+Alt+Space -> push-to-talk press, release', ptt.join() === 'press,release', ptt.join());
    target.lines.length = 0; floatW.lines.length = 0;
    signals.length = 0;
    await keys(K.esc);
    await sleep(150);
    ok('Escape without grab reaches the app, no signal', !signals.some(s => s.name === 'Shortcut' && s.args[0] === 'escape'),
        `app saw: ${[...target.lines, ...floatW.lines].join(',')}`);
    await call('SetEscapeGrab', '(b)', [true]);
    target.lines.length = 0; floatW.lines.length = 0;
    await keys(K.esc);
    await sleep(150);
    ok('Escape with grab -> Shortcut escape, app does not see it',
        signals.some(s => s.name === 'Shortcut' && s.args[0] === 'escape') && ![...target.lines, ...floatW.lines].some(l => l.includes('65307')),
        `app saw: ${[...target.lines, ...floatW.lines].join(',')}`);
    await call('SetEscapeGrab', '(b)', [false]);
    await call('Subscribe', '(a{sv})', [{windows: B(true), gestures: B(true)}]);

    // 9. Screenshots.
    const shots = `${ROOT}/rt/shots`;
    GLib.mkdir_with_parents(shots, 0o700);
    const S = (extra = {}) => ({dir: new GLib.Variant('s', shots), ...extra});
    const timeShot = async opts => {
        const t0 = now();
        const res = await call('Screenshot', '(a{sv})', [opts]);
        return [res, now() - t0];
    };
    const blinks0 = (await probeNow()).blinks;
    await dbg('motion', 300, 250);
    await sleep(50);
    const [[full], tFull] = await timeShot(S({hide_floating: B(false)}));
    const pf = pixel(full, 300, 250);
    ok('full screenshot (floating visible)', pf.w === 1280 && pf.h === 800 && pf.rgb[0] > 200 && pf.rgb[2] < 50,
        `${full} ${pf.w}x${pf.h} rgb=${pf.rgb} ${ms(tFull)} ms`);
    const [[hid], tHid] = await timeShot(S());
    const ph = pixel(hid, 300, 250);
    ok('full screenshot hides the floating window by default', ph.rgb[2] > 200 && ph.rgb[0] < 50, `rgb=${ph.rgb} ${ms(tHid)} ms`);
    const [[area, geo, scale], tArea] = await timeShot(S({
        area: new GLib.Variant('(iiii)', [250, 200, 200, 120]), cursor: B(true), hide_floating: B(false)}));
    const pa = pixel(area, 60, 60);
    ok('area screenshot with cursor', pa.w === 200 && pa.h === 120, `${pa.w}x${pa.h} geo=${geo} scale=${scale} ${ms(tArea)} ms`);
    const [[areaNc]] = await timeShot(S({area: new GLib.Variant('(iiii)', [250, 200, 200, 120]), hide_floating: B(false)}));
    const differs = GLib.compute_checksum_for_data(GLib.ChecksumType.SHA256, GLib.file_get_contents(area)[1]) !==
        GLib.compute_checksum_for_data(GLib.ChecksumType.SHA256, GLib.file_get_contents(areaNc)[1]);
    ok('cursor:true changes the image (cursor composited)', differs);
    e = await errName('Screenshot', '(a{sv})', [S()]);
    ok('5th screenshot within a second -> RateLimited', e === `${ERR}RateLimited`, e);
    await sleep(1100);
    const [[wshot, wgeo]] = await timeShot(S({window: new GLib.Variant('t', tgWin.id)}));
    const pw = pixel(wshot, 10, 10);
    ok('Screenshot{window}: geometry = the window frame', wgeo.join() === tg.join() && pw.w === tg[2] && pw.h === tg[3] && pw.rgb[2] > 200,
        `geo=${wgeo} frame=${tg} ${pw.w}x${pw.h} rgb=${pw.rgb}`);
    e = await errName('Screenshot', '(a{sv})', [S({window: new GLib.Variant('t', 987654321)})]);
    ok('Screenshot of a missing window -> NotFound', e === `${ERR}NotFound`, e);
    e = await errName('Screenshot', '(a{sv})', [S({monitor: new GLib.Variant('i', 7)})]);
    ok('Screenshot of a missing monitor -> NotFound', e === `${ERR}NotFound`, e);
    await sleep(1100);
    const tt = [];
    for (let i = 0; i < 8; i++) {
        tt.push((await timeShot(S({hide_floating: B(false)})))[1]);
        await sleep(260);
    }
    print(`  full 1280x800 screenshot: p50 ${ms(pct(tt, 0.5))} ms, max ${ms(Math.max(...tt))} ms`);
    ok('8 screenshots at under 4/s are not rate limited', tt.length === 8);
    probe = await probeNow();
    ok('the indicator blinks on every screenshot', probe.blinks - blinks0 === 13, `${probe.blinks - blinks0}`);
    const fmode = Gio.File.new_for_path(full).query_info('unix::mode', 0, null).get_attribute_uint32('unix::mode') & 0o777;
    ok('screenshot file is 0600', fmode === 0o600, fmode.toString(8));
    GLib.spawn_command_line_sync(`ln -sfn ${shots} ${ROOT}/rt/shots-link`);
    for (const [bad, why] of [['/tmp', 'outside home/runtime'], [`${ROOT}/rt/shots-link`, 'symlink']]) {
        e = await errName('Screenshot', '(a{sv})', [{dir: new GLib.Variant('s', bad)}]);
        ok(`Screenshot rejects dir (${why}) -> InvalidArgs`, e === `${ERR}InvalidArgs`, e);
    }

    // 10. ForcePassthrough is released when its connection closes.
    await call('ForcePassthrough', '(b)', [true], IFACE, other);
    ok('ForcePassthrough from another connection (the helper)', (await probeNow()).passthrough);
    other.close_sync(null);
    await sleep(300);
    ok('closing that connection releases ForcePassthrough', !(await probeNow()).passthrough);

    // 11. Release.
    await call('SetFloatingWindow', '(a{sv})', [{}]);
    probe = await probeNow();
    ok('release: floating cleared', !probe.floating);

    // 11b. Rule first, window later: the Electron flow (CONTRACT §4.2).
    signals.length = 0;
    const [early] = await call('SetFloatingWindow', '(a{sv})', [{title: new GLib.Variant('s', 'drakter-late')}]);
    ok('rule before the window exists: found = false', early === false);
    const late = spawnWin('drakter-late', '#00ff00', 1280, 799);
    const fwc = await waitSignal(s => s.name === 'FloatingWindowChanged' && s.args[0] === true, 5000);
    ok('FloatingWindowChanged(true) when it maps', fwc?.args[1]?.title === 'drakter-late', JSON.stringify(fwc?.args[1]?.title));
    await sleep(600);
    const [w3] = await call('ListWindows');
    const top = w3[0];
    ok('late window: on top and covering the monitor', top?.title === 'drakter-late' && top.frame.join() === '0,0,1280,799' && top.above,
        `${top?.title} ${top?.frame} above=${top?.above} late=${late.lines}`);
    ok('late window: does not keep the focus', await activeTitle() !== 'drakter-late', await activeTitle());
    await call('SetFloatingWindow', '(a{sv})', [{}]);

    // 12. Cost of the 8 ms button poll in the shell process (idle pointer).
    const [shellPid] = (await bus.call('org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus',
        'GetConnectionUnixProcessID', new GLib.Variant('(s)', [NAME]), null, 0, -1, null)).deepUnpack();
    const cpu = () => {
        const f = new TextDecoder().decode(GLib.file_get_contents(`/proc/${shellPid}/stat`)[1]).split(') ')[1].split(' ');
        return (+f[11] + +f[12]) * 10; // utime+stime, ms (CLK_TCK=100)
    };
    const measure = async () => {
        const c0 = cpu(), t0 = now();
        await sleep(3000);
        return (cpu() - c0) / ((now() - t0) / 1e6) / 10; // percent of one core
    };
    await call('Subscribe', '(a{sv})', [{buttons: B(true)}]);
    const withPoll = await measure();
    await call('Unsubscribe');
    const noPoll = await measure();
    print(`  gnome-shell CPU, idle: 8 ms button poll ${withPoll.toFixed(2)} %, nothing ${noPoll.toFixed(2)} % of one core`);

    // The test windows stay open (they die with the private session): killing the
    // focused test client crashes gnome-shell 50.1 in shell_app_compare() from the
    // shell's own focus-app handler (spike 02 §6.7), not from the extension.
    const failed = results.filter(x => !x[1]);
    print(`\nSUMMARY ${results.length - failed.length}/${results.length} passed${failed.length ? `; failed: ${failed.map(f => f[0]).join('; ')}` : ''}`);
    return failed.length ? 1 : 0;
}

const loop = new GLib.MainLoop(null, false);
let rc = 1;
main().then(x => (rc = x)).catch(err => print(`ERROR ${err}\n${err.stack}`)).finally(() => loop.quit());
loop.run();
System.exit(rc);
