#!/usr/bin/python3
# SPDX-License-Identifier: MIT
"""Run under dbus-run-session + Xvfb; all service operations use a fake adapter."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_backend import Backend, FakeSystem
from xmqr_manager import create_application
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, GLib, Gtk


def main():
    fake = FakeSystem()
    fake.units.append('xmqr-admin.service')
    backend = Backend(fake, registry='/nonexistent-xmqr-gui-fixture', exists=lambda _: True)
    app = create_application(backend)
    failures = []
    def check():
        try:
            assert not app.busy
            assert len(app.entries) == 5
            for row in app.model:
                if row[3] == 'broker':
                    app.tree.get_selection().select_iter(row.iter)
                    break
            assert app.buttons['stop'].get_sensitive()
            assert app.buttons['restart'].get_sensitive()
            assert not app.buttons['start'].get_sensitive()
            assert app.all_buttons['restart'].get_sensitive()
            app.control('stop')
            GLib.timeout_add(700, check_stopped)
        except Exception as exc:
            failures.append(repr(exc))
            app.quit()
        return False
    def check_stopped():
        try:
            assert not app.busy
            assert app.selected().state == 'stopped'
            assert app.buttons['start'].get_sensitive()
            assert not app.buttons['stop'].get_sensitive()
            app.control_all('restart')
            GLib.timeout_add(700, check_restarted)
        except Exception as exc:
            failures.append(repr(exc))
            app.quit()
        return False
    def check_restarted():
        try:
            assert not app.busy
            assert all(e.state in ('running', 'cli') for e in app.entries)
            assert app.all_buttons['stop'].get_sensitive()
            assert not app.all_buttons['start'].get_sensitive()
            window = app.window.get_window()
            pixbuf = Gdk.pixbuf_get_from_window(window, 0, 0, *app.window.get_size())
            pixbuf.savev('/tmp/xmqr-manager-ubuntu.png', 'png', [], [])
            app.error('Falha simulada: autenticação cancelada.')
            assert any(isinstance(w, Gtk.MessageDialog) for w in Gtk.Window.list_toplevels())
            for w in Gtk.Window.list_toplevels():
                if isinstance(w, Gtk.MessageDialog):
                    w.destroy()
            fake.fail = True
            app.refresh()
            GLib.timeout_add(700, check_unavailable)
        except Exception as exc:
            failures.append(repr(exc))
            app.quit()
        return False
    def check_unavailable():
        try:
            assert not app.entries
            assert app.refresh_error
            assert not app.buttons['start'].get_sensitive()
            assert not app.buttons['stop'].get_sensitive()
            assert not app.all_buttons['restart'].get_sensitive()
            print('GTK PASS: discovery, selection, individual stop, batch restart, controls, error dialog, stale-state invalidation, screenshot')
        except Exception as exc:
            failures.append(repr(exc))
        app.quit()
        return False
    GLib.timeout_add(1000, check)
    GLib.timeout_add_seconds(12, lambda: (failures.append('GUI deadline'), app.quit(), False)[-1])
    app.run([sys.argv[0]])
    if failures:
        raise AssertionError(failures)


if __name__ == '__main__':
    main()
