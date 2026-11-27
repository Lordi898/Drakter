// Stand-in for Drakter's Electron main in client.js: a copy of gjs-console placed at
// <ROOT>/fake/desktop/node_modules/electron/dist/electron, next to a package.json named
// drakter-desktop, so the extension's caller check sees the dev layout of Drakter.
// usage: <fake electron> -m fake-drakter.js <token> [<helper script>]
// Prints "MAIN <OK|error>", then "HELPER <OK|error>" for a helper started as its child,
// and then stays connected until it is killed.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
Gio._promisify(Gio.DBusConnection.prototype, 'call');
Gio._promisify(Gio.Subprocess.prototype, 'communicate_utf8_async');

const [token, helper] = ARGV;
const loop = new GLib.MainLoop(null, false);

async function main() {
    try {
        await Gio.DBus.session.call('org.drakter.Companion', '/org/drakter/Companion', 'org.drakter.Companion1',
            'Hello', new GLib.Variant('(s)', [token]), null, Gio.DBusCallFlags.NONE, 5000, null);
        print('MAIN OK');
    } catch (e) {
        print(`MAIN ${Gio.DBusError.get_remote_error(e) ?? e.message}`);
        return false;
    }
    if (helper) {
        const proc = Gio.Subprocess.new(['/usr/bin/python3', '-I', helper, token], Gio.SubprocessFlags.STDOUT_PIPE);
        const [out] = await proc.communicate_utf8_async(null, null);
        print(`HELPER ${out.trim()}`);
    }
    return true;
}

// With a helper it stays connected (a live main); without one it exits after Hello.
main().then(stay => {
    if (!stay || !helper)
        loop.quit();
});
loop.run();
