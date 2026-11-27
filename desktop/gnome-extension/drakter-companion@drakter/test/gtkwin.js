// Test window for the headless shell: prints every click it receives.
// usage: gjs -m gtkwin.js <title> <css-color> <width> <height>
import Gtk from 'gi://Gtk?version=4.0';
import GLib from 'gi://GLib';
const [title, color, w, h] = ARGV;
const app = new Gtk.Application({application_id: `org.drakter.test.${title.replace(/[^a-z]/gi, '')}`});
app.connect('activate', () => {
    const win = new Gtk.ApplicationWindow({application: app, title, default_width: +w, default_height: +h, decorated: false});
    const css = new Gtk.CssProvider();
    css.load_from_string(`window { background: ${color}; }`);
    Gtk.StyleContext.add_provider_for_display(win.get_display(), css, 800);
    const click = new Gtk.GestureClick({button: 0});
    click.connect('pressed', (_g, n, x, y) => print(`CLICK ${title} ${Math.round(x)} ${Math.round(y)} t=${GLib.get_monotonic_time()}`));
    win.add_controller(click);
    const keys = new Gtk.EventControllerKey();
    keys.connect('key-pressed', (_c, keyval) => { print(`KEY ${title} ${keyval}`); return false; });
    win.add_controller(keys);
    win.present();
    print(`READY ${title}`);
});
app.run([]);
