#!/usr/bin/python3
# SPDX-License-Identifier: MIT
"""XMQR Manager for SSH terminals. Shares the Ubuntu desktop's systemd backend."""
import argparse
import os
from pathlib import Path
import shlex
import sys

# Use the adjacent, root-owned backend when installed; no GTK imports.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from backend import (Backend, JOURNALCTL, ManagerError, STATES, SYSTEMCTL,
                     control_plan, enabled, run as base_run)

VERSION = '0.1.0-rc.1'
ACTIONS = ('start', 'stop', 'restart')


def is_root():
    return getattr(os, 'geteuid', lambda: -1)() == 0


def terminal_run(argv, timeout=12):
    """Keep allowlisted tools and terminal privileges; never invoke a shell/polkit."""
    if not argv or argv[0] not in (SYSTEMCTL, JOURNALCTL):
        raise ManagerError('Ferramenta fora da lista permitida.')
    if argv[0] == SYSTEMCTL:
        if len(argv) < 2 or argv[1] not in (*ACTIONS, 'show', 'list-units', 'list-unit-files'):
            raise ManagerError('Comando systemd fora da lista permitida.')
        if argv[1] in ACTIONS and not is_root():
            raise ManagerError('Controle exige root. Execute com sudo xmqr-manager-terminal.')
        argv = [SYSTEMCTL, '--no-ask-password', *argv[1:]]
    return base_run(argv, timeout=timeout)


class TerminalBackend(Backend):
    def __init__(self, runner=terminal_run, config_exists=None, **kwargs):
        super().__init__(runner=runner, **kwargs)
        self.config_exists = config_exists or (lambda p: Path(p).is_file())

    def check_configs(self, plan):
        for id_, action in plan:
            if action not in ('start', 'restart'):
                continue
            component = self.resolve(id_)
            if component.kind == 'client':
                try:
                    available = component.config and self.config_exists(component.config)
                except OSError as exc:
                    raise ManagerError('Nao foi possivel conferir a configuracao do client.') from exc
                if not available:
                    raise ManagerError(f'Configuracao do client indisponivel: {id_}. Nenhuma etapa iniciada.')

    def control(self, id_, action):
        self.check_configs([(id_, action)])
        return super().control(id_, action)

    def journal(self, id_):
        component = self.resolve(id_)
        if not component.service:
            raise ManagerError('Componente sem servico; journal indisponivel.')
        # Output stays on the operator's terminal; no evidence/log files created.
        return self.run([JOURNALCTL, '--unit', component.service, '--lines=300',
                         '--no-pager', '--output=short-iso'], timeout=60)


def choose(entries, target):
    if target == 'client':
        clients = [e for e in entries if e.component.kind == 'client' and e.component.service]
        if len(clients) == 1:
            return clients[0]
        if len(clients) > 1:
            raise ManagerError('Ha varios clients. Use o ID completo mostrado em status.')
    entry = next((e for e in entries if e.component.id == target), None)
    if entry is None:
        raise ManagerError('Componente nao instalado. Consulte os IDs em status.')
    return entry


def operation_plan(entries, target, action):
    if target == 'all':
        return control_plan(entries, action)
    entry = choose(entries, target)
    if action not in ACTIONS or not enabled(action, entry.state):
        raise ManagerError('Acao indisponivel para o estado atual do servico.')
    return [(entry.component.id, action)]


def status(entries):
    if not entries:
        print('Nenhum software XMQR instalado foi encontrado.')
        return
    print(f'{"ID":<34} {"ESTADO":<27} SERVICO')
    colors = {'running': '32', 'failed': '31', 'stopped': '33', 'pending': '33'}
    color = sys.stdout.isatty() and os.environ.get('TERM') != 'dumb' and 'NO_COLOR' not in os.environ
    for entry in entries:
        label = STATES[entry.state]
        text = f'{entry.component.id:<34} {label:<27} {entry.component.service or "CLI"}'
        if color and entry.state in colors:
            text = f'\033[{colors[entry.state]}m{text}\033[0m'
        print(text)
        if entry.detail:
            print('  ' + entry.detail)
    print('Em execucao e estado systemd; nao comprova readiness MQTT ou entrega ao dispositivo.')


def execute(backend, action, target='all', dry_run=False):
    if dry_run and action not in ACTIONS:
        raise ManagerError('--dry-run aplica-se a start, stop ou restart.')
    if action == 'status':
        status(backend.snapshot())
        return
    if action in ACTIONS:
        if not dry_run and not is_root():
            raise ManagerError('Controle exige root. Use sudo xmqr-manager-terminal ' + action + ' ' + target)
        entries = backend.snapshot()
        plan = operation_plan(entries, target, action)
        backend.check_configs(plan)
        if dry_run:
            by_id = {e.component.id: e.component for e in entries}
            print('PLANO: nenhuma alteracao executada. O estado sera revalidado na execucao.')
            for id_, step in plan:
                print(shlex.join([SYSTEMCTL, '--no-ask-password', step, by_id[id_].service]))
            if not plan:
                print('Nenhuma etapa necessaria para o estado atual.')
            return
        if target == 'all':
            result = backend.control_all(action)
        else:
            result = [backend.control(plan[0][0], action)]
        status(result)
        return
    entries = backend.snapshot()
    selected = entries if target == 'all' else [choose(entries, target)]
    if not selected:
        raise ManagerError('Nenhum componente XMQR instalado.')
    if action == 'logs':
        services = [e for e in selected if e.component.service]
        if not services:
            raise ManagerError('Nenhum servico com journal neste alvo.')
        for entry in services:
            print(f'--- {entry.component.id}: ultimas 300 entradas ---')
            print(backend.journal(entry.component.id))
    elif action == 'paths':
        for entry in selected:
            component = entry.component
            print(component.id)
            for field in ('executable', 'service', 'config', 'config_dir', 'certificates', 'panel'):
                value = getattr(component, field)
                if value:
                    print(f'  {field}: {value}')
        print('Caminhos do inventario; conteudo privado nao foi lido. Caminhos podem ser personalizados.')
    else:
        raise ManagerError('Acao invalida.')


def menu(backend):
    options = {'1': 'status', '2': 'start', '3': 'stop', '4': 'restart', '5': 'logs', '6': 'paths'}
    while True:
        print(f'\nXMQR Manager Terminal {VERSION}')
        try:
            status(backend.snapshot())
            print('\n1 Status | 2 Iniciar | 3 Parar | 4 Reiniciar | 5 Logs | 6 Caminhos | 0 Sair')
            choice = input('Opcao: ').strip()
            if choice == '0':
                return
            action = options.get(choice)
            if not action:
                print('Opcao invalida.')
                continue
            target = 'all' if action == 'status' else input('Alvo (broker/admin/client/all ou ID completo): ').strip()
            execute(backend, action, target)
        except ManagerError:
            # Preserve a failing exit status through the CLI's common handler.
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', action='version', version=f'XMQR Manager Terminal {VERSION}')
    parser.add_argument('--dry-run', action='store_true', help='mostrar plano sem controlar servicos')
    parser.add_argument('action', nargs='?', default='menu',
                        choices=('menu', 'status', *ACTIONS, 'logs', 'paths'))
    parser.add_argument('target', nargs='?', default='all', help='broker, admin, client, all ou ID do status')
    args = parser.parse_args()
    if args.dry_run and args.action not in ACTIONS:
        parser.error('--dry-run requer start, stop ou restart')
    if not sys.platform.startswith('linux') or not Path('/run/systemd/system').is_dir():
        parser.error('Operacao requer Linux com systemd ativo. Help/version sao portaveis.')
    backend = TerminalBackend()
    if args.action == 'menu':
        if not sys.stdin.isatty():
            parser.error('Menu requer terminal interativo. Use status para consultas por comando.')
        menu(backend)
    else:
        execute(backend, args.action, args.target, args.dry_run)


if __name__ == '__main__':
    try:
        main()
    except ManagerError as error:
        print(f'ERRO: {error}', file=sys.stderr)
        raise SystemExit(1) from error
    except (EOFError, KeyboardInterrupt):
        print('\nEncerrado pelo operador.')
        raise SystemExit(130)
