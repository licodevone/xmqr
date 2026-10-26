#!/usr/bin/python3
# SPDX-License-Identifier: MIT
"""Local XMQR inventory and systemd adapter. No shell, service or ACL setup."""
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import re
import stat
import subprocess
from urllib.parse import quote, urlsplit

SYSTEMCTL = '/usr/bin/systemctl'
JOURNALCTL = '/usr/bin/journalctl'
REGISTRY = Path('/etc/xmqr-manager/components.d')
MAX_COMPONENTS = 64
INSTANCE = r'[A-Za-z0-9_-]{1,64}'
CLIENT_UNIT = re.compile(rf'xmqr-client-(pub|sub|bridge)@({INSTANCE})\.service\Z')
STATES = {
    'running': 'Em execução', 'stopped': 'Parado', 'pending': 'Em transição',
    'failed': 'Falha', 'unknown': 'Estado indisponível', 'cli': 'CLI instalada; sem serviço',
}


class ManagerError(Exception):
    """An actionable error safe to show in the local desktop."""


def local_path(value):
    return (isinstance(value, str) and value.startswith('/') and not value.startswith('//')
            and len(value) <= 4096 and '..' not in value.split('/')
            and not any(ord(c) < 32 or ord(c) == 127 for c in value))


def panel_url(value):
    if not isinstance(value, str):
        return False
    try:
        url = urlsplit(value)
        return (url.scheme == 'http' and url.hostname in ('127.0.0.1', '::1')
                and url.username is None and url.password is None
                and url.port is not None and 0 < url.port <= 65535
                and url.path in ('', '/') and not url.query and not url.fragment
                and not any(ord(c) < 33 for c in value))
    except ValueError:
        return False


def valid_unit(kind, unit):
    if kind == 'broker':
        return unit == 'xmqr-broker.service'
    if kind == 'admin':
        return unit == 'xmqr-admin.service'
    return kind == 'client' and CLIENT_UNIT.fullmatch(unit) is not None


@dataclass(frozen=True)
class Component:
    id: str
    kind: str
    name: str
    executable: str
    service: str | None = None
    config: str | None = None
    config_dir: str | None = None
    certificates: str | None = None
    logs: str | None = None
    panel: str | None = None

    def validate(self):
        if (not isinstance(self.id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', self.id)
                or self.kind not in ('broker', 'client', 'admin')
                or not isinstance(self.name, str) or not 1 <= len(self.name) <= 120
                or any(ord(c) < 32 or ord(c) == 127 for c in self.name)
                or not local_path(self.executable)
                or any(p is not None and not local_path(p)
                       for p in (self.config, self.config_dir, self.certificates, self.logs))
                or (self.service is not None and
                    (not isinstance(self.service, str) or not valid_unit(self.kind, self.service)))
                or (self.panel is not None and not panel_url(self.panel))):
            raise ManagerError('Registro de componente inválido.')
        return self


@dataclass(frozen=True)
class Entry:
    component: Component
    state: str
    detail: str = ''


def run(argv, timeout=12):
    """All privileged requests go through the desktop polkit agent, never sudo."""
    try:
        result = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True,
                                text=True, errors='replace', timeout=timeout,
                                env={**os.environ, 'LC_ALL': 'C', 'SYSTEMD_COLORS': '0',
                                     'SYSTEMD_PAGER': 'cat', 'SYSTEMD_PAGERSECURE': '1'})
    except subprocess.TimeoutExpired as exc:
        raise ManagerError('Prazo excedido; confira o estado antes de repetir.') from exc
    except OSError as exc:
        raise ManagerError(f'Ferramenta indisponível: {argv[0]}') from exc
    if result.returncode:
        # Do not expose ExecStart, environment or journal contents in errors.
        raise ManagerError('Operação recusada ou não concluída. Confira a autenticação, '
                           'a instalação e o estado do serviço.')
    if len(result.stdout) > 2 * 1024 * 1024:
        raise ManagerError('Resposta do sistema excedeu o limite de 2 MiB.')
    return result.stdout


class Backend:
    def __init__(self, runner=run, registry=REGISTRY, exists=None):
        self.run = runner
        self.registry = Path(registry)
        self.exists = exists or (lambda p: Path(p).is_file() and os.access(p, os.X_OK))

    def registered(self):
        components = {}
        try:
            try:
                with os.scandir(self.registry) as entries:
                    files = sorted(Path(e.path) for e in entries if e.name.endswith('.json'))
            except FileNotFoundError:
                return components
            if len(files) > MAX_COMPONENTS:
                raise ManagerError('Limite de 64 registros excedido.')
            if files:
                # Every ancestor must be controlled by root; otherwise entries
                # could be replaced through a writable directory or symlink.
                for directory in (self.registry, *self.registry.parents):
                    info = directory.lstat()
                    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != 0
                            or info.st_mode & 0o022):
                        raise ManagerError('Diretório de inventário deve pertencer a root e não permitir escrita de grupo/outros.')
            for file in files:
                info = file.lstat()
                if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0
                        or info.st_mode & 0o022 or info.st_size > 16384):
                    raise ManagerError('Registro deve ser arquivo root, sem escrita de grupo/outros, até 16 KiB.')
                with file.open(encoding='utf-8') as stream:
                    raw = stream.read(16385)
                if len(raw.encode('utf-8')) > 16384:
                    raise ManagerError('Registro excedeu 16 KiB.')
                component = Component(**json.loads(raw)).validate()
                if component.id in components:
                    raise ManagerError('ID duplicado no inventário.')
                components[component.id] = component
        except (OSError, TypeError, ValueError) as exc:
            raise ManagerError('Não foi possível ler o inventário protegido do Manager.') from exc
        return components

    def inventory(self):
        components = {
            'broker': Component('broker', 'broker', 'XMQR Broker', '/usr/bin/mqtt-broker',
                                service='xmqr-broker.service', config='/etc/xmqr/broker.env',
                                config_dir='/etc/xmqr', certificates='/etc/xmqr'),
            # The published admin package has no systemd service or default
            # authenticated panel configuration. Explicit registration adds them.
            'admin': Component('admin', 'admin', 'XMQR Admin', '/usr/bin/xmqr-admin',
                               service='xmqr-admin.service'),
            'client': Component('client', 'client', 'XMQR Client', '/usr/bin/mqtt-client',
                                config_dir='/etc/xmqr-client'),
        }
        units = set()
        for command in ('list-units', 'list-unit-files'):
            output = self.run([SYSTEMCTL, command, '--all', '--no-legend', '--plain', '--no-pager',
                               'xmqr-broker.service', 'xmqr-admin.service', 'xmqr-client-*.service'])
            units.update(line.split()[0] for line in output.splitlines() if line.split())
        for unit in sorted(units):
            match = CLIENT_UNIT.fullmatch(unit)
            if not match:
                continue
            mode, instance = match.groups()
            id_ = f'client-{mode}-{instance}'
            binary = '/usr/bin/mqtt-bridge' if mode == 'bridge' else '/usr/bin/mqtt-client'
            config = f'/etc/xmqr-client/bridge-{instance}.toml' if mode == 'bridge' else f'/etc/xmqr-client/{instance}.conf'
            certificates = None if mode == 'bridge' else f'/etc/xmqr-client/{instance}'
            components[id_] = Component(id_, 'client', f'XMQR Client {mode} — {instance}',
                                         binary, service=unit, config=config,
                                         config_dir='/etc/xmqr-client', certificates=certificates)
        registrations = self.registered()
        components.update(registrations)
        if len(components) > MAX_COMPONENTS:
            raise ManagerError('Limite de 64 componentes excedido.')
        result = []
        for component in components.values():
            component.validate()
            if not self.exists(component.executable):
                continue
            if component.service not in units:
                # A registered service that vanished is a real error, not CLI.
                if component.id not in ('broker', 'admin', 'client') or component.id in registrations:
                    pass
                elif component.service:
                    component = Component(**{**asdict(component), 'service': None})
            result.append(component)
        return sorted(result, key=lambda c: c.id)

    def status(self, component):
        if not component.service:
            return Entry(component, 'cli')
        try:
            output = self.run([SYSTEMCTL, 'show', '--no-pager', '--property=LoadState,ActiveState,SubState,ExecStart',
                               component.service])
            props = dict(line.split('=', 1) for line in output.splitlines() if '=' in line)
            if props.get('LoadState') != 'loaded':
                return Entry(component, 'unknown', 'Serviço não carregado ou não instalado.')
            expected = re.search(r'(?:^|[ {;])path=([^ ;}]+)', props.get('ExecStart', ''))
            if not expected or expected.group(1) != component.executable:
                return Entry(component, 'unknown', 'Executável do serviço difere do inventário; controle bloqueado.')
            active = props.get('ActiveState')
            state = {'active': 'running', 'inactive': 'stopped', 'failed': 'failed',
                     'activating': 'pending', 'deactivating': 'pending',
                     'reloading': 'pending'}.get(active, 'unknown')
            if active == 'active' and props.get('SubState') != 'running':
                state = 'unknown'
            return Entry(component, state)
        except ManagerError as exc:
            return Entry(component, 'unknown', str(exc))

    def snapshot(self):
        return [self.status(c) for c in self.inventory()]

    def resolve(self, id_):
        component = next((c for c in self.inventory() if c.id == id_), None)
        if component is None:
            raise ManagerError('Componente não está mais instalado.')
        return component

    def control(self, id_, action):
        if action not in ('start', 'stop', 'restart'):
            raise ManagerError('Ação inválida.')
        component = self.resolve(id_)
        entry = self.status(component)
        if not enabled(action, entry.state):
            raise ManagerError('Ação indisponível para o estado atual do serviço.')
        self.run([SYSTEMCTL, action, component.service], timeout=50)
        entry = self.status(component)
        wanted = 'stopped' if action == 'stop' else 'running'
        if entry.state != wanted:
            raise ManagerError('Comando recebido, mas serviço não atingiu o estado esperado. Confira os logs.')
        return entry

    def journal(self, id_):
        component = self.resolve(id_)
        if not component.service:
            raise ManagerError('Componente sem serviço; journal indisponível.')
        # pkexec uses the desktop authentication agent; no shell and no pager.
        return self.run(['/usr/bin/pkexec', JOURNALCTL, '--unit', component.service,
                         '--lines=300', '--no-pager', '--output=short-iso'], timeout=60)

    def control_all(self, action):
        plan = control_plan(self.snapshot(), action)
        completed = 0
        for id_, step in plan:
            try:
                current = self.status(self.resolve(id_))
                wanted = 'running' if step == 'start' else 'stopped'
                if current.state != wanted:
                    self.control(id_, step)
                completed += 1
            except ManagerError as exc:
                raise ManagerError(f'Operação geral interrompida em {id_}: {exc} '
                                   f'{completed} etapa(s) concluída(s); confira os estados.') from exc
        return self.snapshot()


def control_plan(entries, action):
    if action not in ('start', 'stop', 'restart'):
        raise ManagerError('Ação inválida.')
    services = [e for e in entries if e.component.service]
    if not services:
        raise ManagerError('Nenhum serviço XMQR instalado.')
    if any(e.state in ('unknown', 'pending', 'cli') for e in services):
        raise ManagerError('Há serviço com estado indisponível ou em transição; atualize antes de operar o conjunto.')
    services.sort(key=lambda e: ({'broker': 0, 'admin': 1, 'client': 2}[e.component.kind], e.component.id))
    plan = []
    if action in ('stop', 'restart'):
        plan.extend((e.component.id, 'stop') for e in reversed(services) if e.state == 'running')
    if action in ('start', 'restart'):
        plan.extend((e.component.id, 'start') for e in services if action == 'restart' or e.state != 'running')
    return plan


def enabled(action, state):
    return (action == 'start' and state in ('stopped', 'failed')
            or action in ('stop', 'restart') and state == 'running')


def path_uri(path, directory=False, access=os.access):
    if not local_path(path):
        raise ManagerError('Caminho não configurado ou inválido.')
    # Do not use exists(): an inaccessible parent is not proof of absence.
    flags = os.R_OK | (os.X_OK if directory else os.W_OK)
    scheme = 'file' if access(path, flags) else 'admin'
    return f'{scheme}://{quote(path, safe="/")}'
