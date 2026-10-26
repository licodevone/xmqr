# SPDX-License-Identifier: MIT
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend import (Backend, Component, ManagerError, control_plan, enabled, local_path, panel_url,
                     path_uri, run, valid_unit)


class FakeSystem:
    def __init__(self):
        self.calls = []
        self.units = ['xmqr-broker.service', 'xmqr-client-sub@factory.service',
                      'xmqr-client-bridge@remote.service', 'sshd.service']
        self.active = 'active'
        self.states = {}
        self.executable = None
        self.fail = False

    def __call__(self, argv, timeout=12):
        self.calls.append((argv, timeout))
        if self.fail:
            raise ManagerError('Autenticação cancelada.')
        if argv[1] in ('list-units', 'list-unit-files'):
            return '\n'.join(f'{unit} enabled' for unit in self.units)
        if argv[1] == 'show':
            unit = argv[-1]
            active = self.states.get(unit, self.active)
            binary = ('/usr/bin/mqtt-broker' if unit == 'xmqr-broker.service' else
                      '/usr/bin/xmqr-admin' if unit == 'xmqr-admin.service' else
                      '/usr/bin/mqtt-bridge' if unit.startswith('xmqr-client-bridge') else '/usr/bin/mqtt-client')
            return f'LoadState=loaded\nActiveState={active}\nSubState=running\nExecStart={{ path={self.executable or binary} ; argv[]=ignored secret }}\n'
        if argv[1] in ('start', 'stop', 'restart'):
            self.states[argv[-1]] = 'inactive' if argv[1] == 'stop' else 'active'
            return ''
        if argv[0] == '/usr/bin/pkexec':
            return 'fixture journal entry'
        raise AssertionError(argv)


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeSystem()
        self.backend = Backend(self.fake, registry='/nonexistent-xmqr-test-registry', exists=lambda _: True)
        self.component = Component('broker', 'broker', 'Broker', '/usr/bin/mqtt-broker', 'xmqr-broker.service')

    def test_only_xmqr_units_and_installed_executables_are_discovered(self):
        self.assertEqual([c.id for c in self.backend.inventory()],
                         ['admin', 'broker', 'client', 'client-bridge-remote', 'client-sub-factory'])
        self.backend.exists = lambda _: False
        self.assertEqual(self.backend.inventory(), [])

    def test_admin_without_unit_is_cli_without_invented_panel_or_config(self):
        admin = self.backend.resolve('admin')
        self.assertIsNone(admin.service)
        self.assertIsNone(admin.panel)
        self.assertIsNone(admin.config)
        self.assertEqual(self.backend.status(admin).state, 'cli')

    def test_instances_use_actual_client_layout(self):
        subscriber = self.backend.resolve('client-sub-factory')
        self.assertEqual(subscriber.config, '/etc/xmqr-client/factory.conf')
        self.assertEqual(subscriber.certificates, '/etc/xmqr-client/factory')
        bridge = self.backend.resolve('client-bridge-remote')
        self.assertEqual(bridge.config, '/etc/xmqr-client/bridge-remote.toml')
        self.assertEqual(bridge.executable, '/usr/bin/mqtt-bridge')

    def test_registered_service_not_installed_remains_unavailable(self):
        registered = Component('admin', 'admin', 'Admin', '/usr/bin/xmqr-admin', 'xmqr-admin.service')
        with patch.object(self.backend, 'registered', return_value={'admin': registered}):
            self.assertEqual(self.backend.resolve('admin').service, 'xmqr-admin.service')

    def test_live_state_and_executable_are_checked_before_control(self):
        self.fake.executable = '/usr/bin/unrelated'
        self.assertEqual(self.backend.status(self.component).state, 'unknown')
        with self.assertRaises(ManagerError):
            self.backend.control('broker', 'restart')
        self.assertFalse(any(a[1] == 'restart' for a, _ in self.fake.calls))

    def test_stop_and_start_wait_for_observed_state(self):
        self.assertEqual(self.backend.control('broker', 'stop').state, 'stopped')
        self.assertIn((['/usr/bin/systemctl', 'stop', 'xmqr-broker.service'], 50), self.fake.calls)
        self.assertEqual(self.backend.control('broker', 'start').state, 'running')

    def test_cancelled_authentication_does_not_report_success(self):
        original = self.fake.__call__
        def fail_action(argv, timeout=12):
            if argv[1] == 'stop':
                raise ManagerError('cancelled')
            return original(argv, timeout)
        self.backend.run = fail_action
        with self.assertRaises(ManagerError):
            self.backend.control('broker', 'stop')

    def test_failed_state_queries_never_become_running(self):
        self.fake.fail = True
        self.assertEqual(self.backend.status(self.component).state, 'unknown')
        with self.assertRaises(ManagerError):
            self.backend.snapshot()

    def test_successful_command_with_wrong_final_state_is_failure(self):
        original = self.fake.__call__
        self.backend.run = lambda argv, timeout=12: '' if argv[1] == 'stop' else original(argv, timeout)
        with self.assertRaises(ManagerError):
            self.backend.control('broker', 'stop')

    def test_arbitrary_actions_and_noninstalled_ids_never_execute(self):
        for action in ['restart; rm -rf /', 'enable', '--help', '']:
            with self.assertRaises(ManagerError):
                self.backend.control('broker', action)
        self.assertEqual(self.fake.calls, [])
        with self.assertRaises(ManagerError):
            self.backend.control('sshd', 'restart')

    def test_journal_has_fixed_unit_limit_and_no_pager(self):
        self.assertEqual(self.backend.journal('broker'), 'fixture journal entry')
        argv, timeout = self.fake.calls[-1]
        self.assertEqual(argv, ['/usr/bin/pkexec', '/usr/bin/journalctl', '--unit',
                                'xmqr-broker.service', '--lines=300', '--no-pager', '--output=short-iso'])
        self.assertEqual(timeout, 60)

    def test_missing_registered_inventory_and_component_cap(self):
        self.assertEqual(self.backend.registered(), {})
        with patch.object(self.backend, 'registered', return_value={str(i): self.component for i in range(65)}):
            with self.assertRaises(ManagerError):
                self.backend.inventory()

    def test_symlink_or_writable_registry_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            registry = Path(temp) / 'registry'
            registry.mkdir()
            (registry / 'broker.json').write_text(json.dumps(self.component.__dict__))
            registry.chmod(0o777)
            with self.assertRaises(ManagerError):
                Backend(registry=registry).registered()

    def test_inaccessible_registry_does_not_become_empty_inventory(self):
        with patch('os.scandir', side_effect=PermissionError('denied')):
            with self.assertRaises(ManagerError):
                self.backend.registered()

    def test_batch_restart_orders_three_services_and_skips_cli(self):
        self.fake.units = ['xmqr-broker.service', 'xmqr-admin.service', 'xmqr-client-sub@factory.service']
        entries = self.backend.control_all('restart')
        actions = [(a[1], a[-1]) for a, _ in self.fake.calls if a[1] in ('start', 'stop', 'restart')]
        self.assertEqual(actions, [('stop', 'xmqr-client-sub@factory.service'), ('stop', 'xmqr-admin.service'),
                                   ('stop', 'xmqr-broker.service'), ('start', 'xmqr-broker.service'),
                                   ('start', 'xmqr-admin.service'), ('start', 'xmqr-client-sub@factory.service')])
        self.assertTrue(all(e.state in ('running', 'cli') for e in entries))

    def test_batch_unknown_state_blocks_before_any_changes(self):
        self.fake.executable = '/usr/bin/mismatched'
        with self.assertRaises(ManagerError):
            self.backend.control_all('stop')
        self.assertFalse(any(a[1] in ('start', 'stop', 'restart') for a, _ in self.fake.calls))

    def test_batch_stops_at_first_error_and_reports_partial_result(self):
        self.fake.units = ['xmqr-broker.service', 'xmqr-admin.service', 'xmqr-client-sub@factory.service']
        original = self.fake.__call__
        def deny(argv, timeout=12):
            if argv[1] == 'stop' and argv[-1] == 'xmqr-broker.service':
                raise ManagerError('cancelled')
            return original(argv, timeout)
        self.backend.run = deny
        with self.assertRaisesRegex(ManagerError, '2 etapa'):
            self.backend.control_all('restart')
        self.assertFalse(any(a[1] == 'start' for a, _ in self.fake.calls))

    def test_batch_start_is_idempotent_and_empty_sets_are_rejected(self):
        self.backend.control_all('start')
        self.assertFalse(any(a[1] in ('start', 'stop') for a, _ in self.fake.calls))
        with self.assertRaises(ManagerError):
            control_plan([], 'restart')
        with self.assertRaises(ManagerError):
            control_plan([], '--help')


class PolicyTests(unittest.TestCase):
    def test_paths_and_urls_reject_commands_traversal_remote_and_credentials(self):
        for value in ['../etc', '/etc/../root', '//host/etc', '/etc/\nkey', 'file:///etc/a']:
            self.assertFalse(local_path(value), value)
        for value in ['https://127.0.0.1:9080', 'http://localhost:9080',
                      'http://127.0.0.1:0', 'http://127.0.0.1:9080@evil',
                      'http://127.0.0.1:9080/?secret=x', 'http://127.0.0.1:99999',
                      'http://[::1', 'http://127.0.0.1:9080\n']:
            self.assertFalse(panel_url(value), value)
        self.assertTrue(panel_url('http://[::1]:9080/'))

    def test_registry_validates_optional_fields_and_service_kind(self):
        component = Component('broker', 'broker', 'Broker', '/usr/bin/mqtt-broker')
        for fields in [{'service': 'sshd.service'}, {'service': 'xmqr-admin.service'},
                       {'config': '/etc/../root/secret'}, {'name': 'secret\n'},
                       {'panel': 'http://remote:9080'}, {'config_dir': 'relative'}]:
            with self.assertRaises(ManagerError):
                replace(component, **fields).validate()
        self.assertEqual(component.validate(), component)

    def test_units_are_fixed_names_and_restricted_instances(self):
        self.assertTrue(valid_unit('client', 'xmqr-client-sub@factory_01.service'))
        for unit in ['xmqr-client-sub@.service', 'xmqr-client-sub@../root.service',
                     'xmqr-client-sub@a;shutdown.service', 'sshd.service', 'xmqr-admin.service']:
            self.assertFalse(valid_unit('client', unit))

    def test_protected_paths_use_admin_uri_without_mutating_permissions(self):
        self.assertEqual(path_uri('/etc/xmqr/a b#é.env', access=lambda *_: False),
                         'admin:///etc/xmqr/a%20b%23%C3%A9.env')
        self.assertEqual(path_uri('/etc/xmqr', directory=True, access=lambda *_: True),
                         'file:///etc/xmqr')

    def test_state_controls_are_disabled_for_missing_failed_queries_or_transition(self):
        for state in ['unknown', 'pending', 'cli']:
            for action in ['start', 'stop', 'restart']:
                self.assertFalse(enabled(action, state))
        self.assertTrue(enabled('start', 'failed'))
        self.assertFalse(enabled('restart', 'stopped'))

    def test_runner_does_not_expose_command_output_in_errors(self):
        result = subprocess.CompletedProcess([], 1, 'secret', 'password')
        with patch('subprocess.run', return_value=result):
            with self.assertRaises(ManagerError) as error:
                run(['/usr/bin/false'])
        self.assertNotIn('secret', str(error.exception))
        self.assertNotIn('password', str(error.exception))

    def test_runner_passes_argv_as_data_and_timeout_is_reported(self):
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('test', 1)) as call:
            with self.assertRaises(ManagerError):
                run(['/usr/bin/test', "a';echo injected"], timeout=1)
        self.assertEqual(call.call_args.args[0][1], "a';echo injected")
        self.assertNotIn('shell', call.call_args.kwargs)


@unittest.skipUnless(os.name == 'posix' and hasattr(os, 'geteuid') and os.geteuid() == 0,
                     'Secure registry fixtures require isolated Linux root environment')
class SecureRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='xmqr-manager-registry-', dir='/opt')
        self.directory = Path(self.temp.name)
        self.directory.chmod(0o755)
        self.path = self.directory / 'admin.json'
        self.component = Component('admin', 'admin', 'Admin', '/usr/bin/xmqr-admin',
                                   'xmqr-admin.service', config='/etc/xmqr-admin/admin.env')
        self.path.write_text(json.dumps(self.component.__dict__))
        self.path.chmod(0o644)
        self.backend = Backend(registry=self.directory)

    def tearDown(self):
        self.temp.cleanup()

    def test_valid_root_owned_registration(self):
        self.assertEqual(self.backend.registered(), {'admin': self.component})

    def test_symlink_registry_file_is_rejected(self):
        link = self.directory / 'link.json'
        link.symlink_to(self.path)
        with self.assertRaises(ManagerError):
            self.backend.registered()

    def test_duplicate_id_and_invalid_json_are_rejected(self):
        extra = self.directory / 'extra.json'
        extra.write_text(self.path.read_text())
        with self.assertRaises(ManagerError):
            self.backend.registered()
        extra.write_text('{')
        with self.assertRaises(ManagerError):
            self.backend.registered()

    def test_oversized_file_and_writable_file_are_rejected(self):
        self.path.chmod(0o666)
        with self.assertRaises(ManagerError):
            self.backend.registered()
        self.path.chmod(0o644)
        self.path.write_text(' ' * 16385)
        with self.assertRaises(ManagerError):
            self.backend.registered()


if __name__ == '__main__':
    unittest.main()
