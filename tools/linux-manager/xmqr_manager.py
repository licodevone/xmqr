#!/usr/bin/python3
# SPDX-License-Identifier: MIT
"""XMQR Manager for Ubuntu GNOME. Privileges stay in systemd/polkit and GVfs."""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
import threading

# The installed launcher uses isolated Python; import only this trusted directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from backend import Backend, ManagerError, STATES, control_plan, enabled, path_uri


def create_application(backend=None):
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gio, GLib, Gtk

    class Application(Gtk.Application):
        def __init__(self):
            super().__init__(application_id='net.acmebr.XMQRManager')
            self.backend = backend or Backend()
            self.entries = []
            self.busy = False
            self.window = None
            self.indicator = None
            self.refresh_error = False
            self.buttons = {}
            self.all_buttons = {}

        def do_activate(self):
            if self.window:
                self.window.present()
                return
            self.window = Gtk.ApplicationWindow(application=self, title='XMQR Manager')
            self.window.set_default_size(960, 600)
            self.window.connect('delete-event', self.close_window)
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16, margin=24)
            self.window.add(box)
            header = Gtk.Box(spacing=12)
            title = Gtk.Label(xalign=0)
            title.set_markup('<span size="xx-large" weight="bold">XMQR Manager</span>')
            header.pack_start(title, True, True, 0)
            self.spinner = Gtk.Spinner()
            header.pack_start(self.spinner, False, False, 0)
            self.refresh_button = Gtk.Button(label='Atualizar')
            self.refresh_button.connect('clicked', lambda _: self.refresh())
            header.pack_start(self.refresh_button, False, False, 0)
            box.pack_start(header, False, False, 0)
            subtitle = Gtk.Label(label='Serviços e arquivos locais · Ubuntu', xalign=0)
            box.pack_start(subtitle, False, False, 0)
            general = Gtk.Box(spacing=8)
            for action, label in (('start', 'Iniciar todos'), ('stop', 'Parar todos'), ('restart', 'Reiniciar todos')):
                button = Gtk.Button(label=label)
                button.connect('clicked', lambda _, a=action: self.control_all(a))
                self.all_buttons[action] = button
                general.pack_start(button, False, False, 0)
            box.pack_start(general, False, False, 0)
            self.model = Gtk.ListStore(str, str, str, str)
            self.tree = Gtk.TreeView(model=self.model)
            for number, label in enumerate(('Sistema', 'Estado', 'Serviço')):
                column = Gtk.TreeViewColumn(label, Gtk.CellRendererText(), text=number)
                column.set_expand(number == 0)
                column.set_resizable(True)
                self.tree.append_column(column)
            self.tree.get_selection().connect('changed', lambda _: self.update_actions())
            scroll = Gtk.ScrolledWindow()
            scroll.set_vexpand(True)
            scroll.add(self.tree)
            box.pack_start(scroll, True, True, 0)
            self.detail = Gtk.Label(xalign=0, wrap=True, selectable=True)
            box.pack_start(self.detail, False, False, 0)
            services = Gtk.Box(spacing=8)
            for action, label in (('start', 'Iniciar'), ('stop', 'Parar'), ('restart', 'Reiniciar')):
                button = Gtk.Button(label=label)
                button.connect('clicked', lambda _, a=action: self.control(a))
                self.buttons[action] = button
                services.pack_start(button, False, False, 0)
            box.pack_start(services, False, False, 0)
            files = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, column_spacing=8, row_spacing=8)
            for action, label in (('config', 'Abrir configuração'), ('config_dir', 'Pasta de configurações'),
                                  ('certificates', 'Certificados'), ('logs', 'Pasta de logs'),
                                  ('journal', 'Logs do serviço'), ('panel', 'Painel Admin')):
                button = Gtk.Button(label=label)
                button.connect('clicked', lambda _, a=action: self.open_target(a))
                self.buttons[action] = button
                files.add(button)
            box.pack_start(files, False, False, 0)
            self.message = Gtk.Label(label='Consultando instalações…', xalign=0, wrap=True, selectable=True)
            box.pack_start(self.message, False, False, 0)
            footer = Gtk.Label(label='Em execução indica o estado do serviço. A conexão MQTT não é verificada.', xalign=0, wrap=True)
            footer.get_style_context().add_class('dim-label')
            box.pack_start(footer, False, False, 0)
            self.setup_indicator(gi, Gtk)
            self.window.show_all()
            if '--background' in sys.argv and self.indicator:
                self.window.hide()
            self.refresh()
            GLib.timeout_add_seconds(5, self.periodic_refresh)

        def setup_indicator(self, gi, Gtk):
            try:
                gi.require_version('AyatanaAppIndicator3', '0.1')
                from gi.repository import AyatanaAppIndicator3 as Indicator
                self.indicator = Indicator.Indicator.new('xmqr-manager', 'network-server',
                                                        Indicator.IndicatorCategory.APPLICATION_STATUS)
                self.indicator.set_title('XMQR Manager')
                self.indicator.set_status(Indicator.IndicatorStatus.ACTIVE)
                self.tray_menu = Gtk.Menu()
                self.indicator.set_menu(self.tray_menu)
                self.update_tray()
            except (ImportError, ValueError):
                self.indicator = None

        def update_tray(self):
            if not self.indicator:
                return
            for child in self.tray_menu.get_children():
                self.tray_menu.remove(child)
            show = Gtk.MenuItem(label='Abrir XMQR Manager')
            show.connect('activate', lambda _: self.window.present())
            self.tray_menu.append(show)
            for action, label in (('start', 'Iniciar todos os serviços'), ('stop', 'Parar todos os serviços'),
                                  ('restart', 'Reiniciar todos os serviços')):
                command = Gtk.MenuItem(label=label)
                command.set_sensitive(self.batch_enabled(action))
                command.connect('activate', lambda _, a=action: self.control_all(a))
                self.tray_menu.append(command)
            for entry in self.entries:
                item = Gtk.MenuItem(label=f'{entry.component.name} — {STATES[entry.state]}')
                submenu = Gtk.Menu()
                for action, label in (('start', 'Iniciar'), ('stop', 'Parar'), ('restart', 'Reiniciar')):
                    command = Gtk.MenuItem(label=label)
                    command.set_sensitive(not self.busy and enabled(action, entry.state))
                    command.connect('activate', lambda _, id_=entry.component.id, a=action: self.control(a, id_))
                    submenu.append(command)
                item.set_submenu(submenu)
                self.tray_menu.append(item)
            quit_item = Gtk.MenuItem(label='Sair (mantém os serviços)')
            quit_item.connect('activate', lambda _: self.quit())
            self.tray_menu.append(quit_item)
            self.tray_menu.show_all()
            if self.refresh_error:
                label = 'XMQR: indisponível'
            elif not self.entries:
                label = 'XMQR: sem componentes'
            elif any(e.state in ('failed', 'unknown') for e in self.entries):
                label = 'XMQR: verificar'
            elif self.busy:
                label = 'XMQR: aguarde'
            elif all(e.state in ('running', 'cli') for e in self.entries):
                label = 'XMQR: ativo' if any(e.state == 'running' for e in self.entries) else 'XMQR: CLI'
            else:
                label = 'XMQR: parado/misto'
            self.indicator.set_label(label, 'XMQR: parado/misto')

        def close_window(self, *_):
            if self.indicator:
                self.window.hide()
                return True
            return False

        def selected(self):
            model, row = self.tree.get_selection().get_selected()
            if row is None:
                return None
            return next((e for e in self.entries if e.component.id == model[row][3]), None)

        def update_actions(self):
            entry = self.selected()
            for action, button in self.buttons.items():
                available = False
                if entry:
                    if action in ('start', 'stop', 'restart'):
                        available = enabled(action, entry.state)
                    elif action == 'journal':
                        available = bool(entry.component.service)
                    else:
                        available = bool(getattr(entry.component, action))
                button.set_sensitive(not self.busy and available)
            self.detail.set_text(entry.detail if entry else 'Selecione um sistema para gerenciar.')
            self.refresh_button.set_sensitive(not self.busy)
            for action, button in self.all_buttons.items():
                button.set_sensitive(self.batch_enabled(action))
            self.update_tray()

        def batch_enabled(self, action):
            if self.busy or self.refresh_error:
                return False
            try:
                return bool(control_plan(self.entries, action))
            except ManagerError:
                return False

        def job(self, task, done, report=True, refresh_after_error=False):
            if self.busy:
                return
            self.busy = True
            self.spinner.start()
            self.update_actions()

            def work():
                try:
                    result, error = task(), None
                except Exception as exc:
                    result, error = None, str(exc)
                GLib.idle_add(finish, result, error)

            def finish(result, error):
                self.busy = False
                self.spinner.stop()
                if error:
                    # An unavailable refresh must invalidate all stale states.
                    if not report:
                        self.refresh_error = True
                        self.entries = []
                        self.model.clear()
                    self.message.set_text(error)
                    if report:
                        self.error(error)
                else:
                    done(result)
                self.update_actions()
                if error and refresh_after_error:
                    self.refresh()
                return False

            threading.Thread(target=work, daemon=True).start()

        def refresh(self):
            def done(entries):
                self.refresh_error = False
                selected = self.selected()
                self.entries = entries
                self.model.clear()
                chosen = None
                for entry in entries:
                    row = self.model.append([entry.component.name, STATES[entry.state],
                                             entry.component.service or '—', entry.component.id])
                    if selected and selected.component.id == entry.component.id:
                        chosen = row
                if chosen is not None:
                    self.tree.get_selection().select_iter(chosen)
                elif entries:
                    self.tree.get_selection().select_path(0)
                self.message.set_text(f'{len(entries)} componente(s) instalado(s).' if entries else
                                      'Nenhum componente XMQR instalado. Instale os pacotes Broker, Client ou Admin.')
            self.job(self.backend.snapshot, done, report=False)

        def periodic_refresh(self):
            if not self.busy:
                self.refresh()
            return True

        def control(self, action, id_=None):
            entry = self.selected()
            id_ = id_ or (entry.component.id if entry else None)
            if id_:
                self.message.set_text('Aguarde a autenticação administrativa e a conclusão do serviço…')
                self.job(lambda: self.backend.control(id_, action), lambda _: self.refresh(), refresh_after_error=True)

        def control_all(self, action):
            if not self.batch_enabled(action):
                return
            self.message.set_text('Operação geral em andamento. Aguarde a autenticação e a conclusão dos serviços…')
            self.job(lambda: self.backend.control_all(action), lambda _: self.refresh(), refresh_after_error=True)

        def error(self, message):
            dialog = Gtk.MessageDialog(transient_for=self.window, modal=True,
                                       message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.CLOSE,
                                       text='Não foi possível concluir a operação')
            dialog.format_secondary_text(message)
            dialog.connect('response', lambda d, _: d.destroy())
            dialog.show()

        def open_target(self, action):
            entry = self.selected()
            if not entry or self.busy:
                return
            if action == 'journal':
                self.job(lambda: self.backend.journal(entry.component.id), self.show_journal)
                return
            try:
                component = self.backend.resolve(entry.component.id)
                if action == 'panel':
                    Gio.AppInfo.launch_default_for_uri(component.panel, None)
                    return
                target = getattr(component, action)
                directory = action != 'config'
                uri = path_uri(target, directory)
                file = Gio.File.new_for_uri(uri)
                mount = Gtk.MountOperation.new(self.window)
                self.busy = True
                self.update_actions()

                def finish(error=None):
                    self.busy = False
                    self.update_actions()
                    if error:
                        self.error(str(error))

                def launch(info):
                    if directory != (info.get_file_type() == Gio.FileType.DIRECTORY):
                        raise ManagerError('O destino não possui o tipo esperado.')
                    if directory:
                        Gio.AppInfo.launch_default_for_uri(uri, None)
                    else:
                        editor = Gio.AppInfo.get_default_for_type('text/plain', True)
                        if not editor:
                            raise ManagerError('Instale um editor de texto com suporte GIO, como gnome-text-editor.')
                        editor.launch_uris([uri], None)

                def query(may_mount=True):
                    file.query_info_async('standard::type', Gio.FileQueryInfoFlags.NONE,
                                          GLib.PRIORITY_DEFAULT, None, queried, may_mount)

                def queried(source, result, may_mount):
                    try:
                        info = source.query_info_finish(result)
                        launch(info)
                        finish()
                    except GLib.Error as exc:
                        if may_mount and exc.matches(Gio.io_error_quark(), Gio.IOErrorEnum.NOT_MOUNTED):
                            file.mount_enclosing_volume(Gio.MountMountFlags.NONE, mount, None, mounted, None)
                        else:
                            finish(exc)
                    except Exception as exc:
                        finish(exc)

                def mounted(source, result, _):
                    try:
                        source.mount_enclosing_volume_finish(result)
                        query(False)
                    except Exception as exc:
                        finish(exc)

                query()
            except Exception as exc:
                self.error(str(exc))

        def show_journal(self, text):
            window = Gtk.Window(title='XMQR — logs do serviço', transient_for=self.window)
            window.set_default_size(1000, 650)
            view = Gtk.TextView(editable=False, monospace=True, cursor_visible=False)
            view.get_buffer().set_text(text or 'Nenhuma entrada no journal.')
            scroll = Gtk.ScrolledWindow()
            scroll.add(view)
            window.add(scroll)
            window.show_all()

    return Application()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', action='version', version='XMQR Manager Ubuntu 0.1.0')
    parser.add_argument('--diagnose', action='store_true', help='Inventário/status JSON sem conteúdo privado')
    parser.add_argument('--background', action='store_true', help='Inicia na bandeja quando disponível')
    args = parser.parse_args()
    try:
        if args.diagnose:
            print(json.dumps({'components': [asdict(e) for e in Backend().snapshot()]}, ensure_ascii=False))
            return 0
        if os.geteuid() == 0:
            raise ManagerError('Inicie o Manager como usuário do desktop. O sistema pedirá autenticação quando necessário.')
        app = create_application()
        return app.run([sys.argv[0]])
    except (ManagerError, ImportError, ValueError) as exc:
        print(f'XMQR Manager: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
