# SPDX-License-Identifier: MIT
import contextlib
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import terminal
from backend import ManagerError
from test_backend import FakeSystem


class TerminalTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeSystem()
        self.fake.units = ['xmqr-broker.service', 'xmqr-admin.service', 'xmqr-client-sub@oracle.service']
        self.backend = terminal.TerminalBackend(runner=self.fake,
            registry='/nonexistent-xmqr-test-registry', exists=lambda _: True, config_exists=lambda _: True)
        self.output = io.StringIO()
        self.capture = contextlib.redirect_stdout(self.output)
        self.capture.__enter__()

    def tearDown(self):
        self.capture.__exit__(None, None, None)

    def mutations(self):
        return [(a[1], a[-1]) for a, _ in self.fake.calls if a[1] in terminal.ACTIONS]

    def test_status_reads_inventory_and_never_controls_services(self):
        terminal.execute(self.backend, 'status')
        self.assertIn('client-sub-oracle', self.output.getvalue())
        self.assertEqual(self.mutations(), [])

    def test_unprivileged_control_is_refused_before_any_backend_call(self):
        with patch.object(terminal, 'is_root', return_value=False):
            with self.assertRaisesRegex(ManagerError, 'root'):
                terminal.execute(self.backend, 'restart', 'all')
        self.assertEqual(self.fake.calls, [])

    def test_dry_run_shows_restart_order_without_root_or_mutation(self):
        with patch.object(terminal, 'is_root', return_value=False):
            terminal.execute(self.backend, 'restart', 'all', dry_run=True)
        plan = [line for line in self.output.getvalue().splitlines() if line.startswith('/usr/bin/systemctl')]
        self.assertIn('stop xmqr-client-sub@oracle.service', plan[0])
        self.assertIn('start xmqr-client-sub@oracle.service', plan[-1])
        self.assertEqual(len(plan), 6)
        self.assertEqual(self.mutations(), [])

    def test_bulk_unknown_state_aborts_before_any_mutation(self):
        self.fake.executable = '/usr/bin/unrelated'
        with patch.object(terminal, 'is_root', return_value=True):
            with self.assertRaises(ManagerError):
                terminal.execute(self.backend, 'stop', 'all')
        self.assertEqual(self.mutations(), [])

    def test_missing_client_config_blocks_entire_restart_before_stop(self):
        self.backend.config_exists = lambda _: False
        with patch.object(terminal, 'is_root', return_value=True):
            with self.assertRaisesRegex(ManagerError, 'Configuracao'):
                terminal.execute(self.backend, 'restart', 'all')
        self.assertEqual(self.mutations(), [])

    def test_external_units_and_shell_fragments_are_never_controlled(self):
        self.fake.units += ['sshd.service', 'xmqr-client-sub@bad;injected.service']
        for target in ['sshd', 'broker;echo injected', '--help', '../admin']:
            with patch.object(terminal, 'is_root', return_value=True):
                with self.assertRaises(ManagerError):
                    terminal.execute(self.backend, 'stop', target)
        self.assertEqual(self.mutations(), [])

    def test_client_alias_requires_one_instance(self):
        entries = self.backend.snapshot()
        self.assertEqual(terminal.choose(entries, 'client').component.id, 'client-sub-oracle')
        self.fake.units += ['xmqr-client-sub@second.service']
        with self.assertRaisesRegex(ManagerError, 'varios'):
            terminal.choose(self.backend.snapshot(), 'client')

    def test_restart_runs_complete_shared_plan_and_checks_final_state(self):
        with patch.object(terminal, 'is_root', return_value=True):
            terminal.execute(self.backend, 'restart', 'all')
        self.assertEqual(self.mutations(), [
            ('stop', 'xmqr-client-sub@oracle.service'), ('stop', 'xmqr-admin.service'),
            ('stop', 'xmqr-broker.service'), ('start', 'xmqr-broker.service'),
            ('start', 'xmqr-admin.service'), ('start', 'xmqr-client-sub@oracle.service')])

    def test_batch_failure_stops_remaining_steps_and_reports_partial_work(self):
        def fail(argv, timeout=12):
            if argv[1] == 'stop' and argv[-1] == 'xmqr-broker.service':
                raise ManagerError('fixture failure')
            return self.fake(argv, timeout)
        self.backend.run = fail
        with patch.object(terminal, 'is_root', return_value=True):
            with self.assertRaisesRegex(ManagerError, '2 etapa'):
                terminal.execute(self.backend, 'restart', 'all')
        self.assertFalse(any(action == 'start' for action, _ in self.mutations()))

    def test_terminal_journal_has_no_pkexec_or_pager_and_finite_limit(self):
        original = self.fake
        calls = []
        def journal(argv, timeout=12):
            if argv[0] == terminal.JOURNALCTL:
                calls.append((argv, timeout))
                return 'SYNTHETIC-JOURNAL'
            return original(argv, timeout)
        self.backend.run = journal
        terminal.execute(self.backend, 'logs', 'broker')
        self.assertEqual(calls, [(['/usr/bin/journalctl', '--unit', 'xmqr-broker.service',
            '--lines=300', '--no-pager', '--output=short-iso'], 60)])

    def test_runner_refuses_unknown_executables_and_rootless_mutations(self):
        with patch.object(terminal, 'base_run') as command:
            for argv in [['/bin/sh', '-c', 'anything'], [terminal.SYSTEMCTL, 'enable', 'xmqr-broker.service']]:
                with self.assertRaises(ManagerError):
                    terminal.terminal_run(argv)
            with patch.object(terminal, 'is_root', return_value=False):
                with self.assertRaises(ManagerError):
                    terminal.terminal_run([terminal.SYSTEMCTL, 'stop', 'xmqr-broker.service'])
            command.assert_not_called()

    def test_runner_keeps_timeout_and_disables_password_agent(self):
        with patch.object(terminal, 'base_run', return_value='OK') as command:
            self.assertEqual(terminal.terminal_run([terminal.SYSTEMCTL, 'show', 'xmqr-broker.service'], 7), 'OK')
        command.assert_called_once_with([terminal.SYSTEMCTL, '--no-ask-password', 'show', 'xmqr-broker.service'], timeout=7)

    def test_menu_exit_is_readonly(self):
        with patch('builtins.input', return_value='0'):
            terminal.menu(self.backend)
        self.assertIn('XMQR Manager Terminal', self.output.getvalue())
        self.assertEqual(self.mutations(), [])

    def test_paths_prints_references_without_reading_private_files(self):
        with patch.object(Path, 'read_text', side_effect=AssertionError('private read')):
            terminal.execute(self.backend, 'paths', 'client')
        self.assertIn('/etc/xmqr-client/oracle.conf', self.output.getvalue())

    def test_menu_action_errors_propagate_to_the_cli_handler(self):
        with patch('builtins.input', side_effect=['3', 'broker']):
            with patch.object(terminal, 'is_root', return_value=False):
                with self.assertRaisesRegex(ManagerError, 'root'):
                    terminal.menu(self.backend)
        self.assertEqual(self.mutations(), [])

    def test_masked_service_blocks_the_complete_batch(self):
        original = self.fake
        def masked(argv, timeout=12):
            result = original(argv, timeout)
            if argv[1] == 'show' and argv[-1] == 'xmqr-admin.service':
                return result.replace('LoadState=loaded', 'LoadState=masked')
            return result
        self.backend.run = masked
        with patch.object(terminal, 'is_root', return_value=True):
            with self.assertRaises(ManagerError):
                terminal.execute(self.backend, 'restart', 'all')
        self.assertEqual(self.mutations(), [])


if __name__ == '__main__':
    unittest.main()
