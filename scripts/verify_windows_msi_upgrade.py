#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise real Broker MSI upgrade/rollback only on a clean hosted Windows VM."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import time
import uuid

from verify_windows_broker_runtime import publish, retained


def powershell(script, **variables):
    result = subprocess.run(
        ["pwsh", "-NoProfile", "-NonInteractive", "-Command", script],
        env=os.environ | variables, capture_output=True, text=True, timeout=60,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"PowerShell exited with code {result.returncode}" + (f": {detail}" if detail else ""))
    return result.stdout.strip()


def metadata(msi):
    text = powershell(r"""
$ErrorActionPreference = 'Stop'
$installer = New-Object -ComObject WindowsInstaller.Installer
$db = $installer.OpenDatabase($env:XMQR_ACCEPTANCE_MSI, 0)
$view = $db.OpenView('SELECT `Property`,`Value` FROM `Property`')
$view.Execute()
$values = @{}
while ($record = $view.Fetch()) { $values[$record.StringData(1)] = $record.StringData(2) }
$view.Close()
@{ product = $values.ProductCode; version = $values.ProductVersion } | ConvertTo-Json -Compress
""", XMQR_ACCEPTANCE_MSI=str(msi))
    return json.loads(text)


def prepare_failure(candidate, destination):
    """Modify only a new test copy; never execute an MSI from this function."""
    if destination.exists():
        raise ValueError("Failure fixture must have a new destination")
    shutil.copyfile(candidate, destination)
    powershell(r"""
$ErrorActionPreference = 'Stop'
$installer = New-Object -ComObject WindowsInstaller.Installer
$db = $installer.OpenDatabase($env:XMQR_ACCEPTANCE_MSI, 1)
$view = $db.OpenView('SELECT `Sequence` FROM `InstallExecuteSequence` WHERE `Action`=''RemoveExistingProducts''')
$view.Execute()
$record = $view.Fetch()
if ($null -eq $record) { throw 'RemoveExistingProducts is absent' }
$sequence = [int]$record.StringData(1)
$view.Close()
if ($sequence -le 1500 -or $sequence -ge 1599) { throw 'Unexpected removal schedule' }
$product = '{' + [guid]::NewGuid().ToString().ToUpperInvariant() + '}'
$commands = @(
  "UPDATE ``Property`` SET ``Value``='$product' WHERE ``Property``='ProductCode'",
  "INSERT INTO ``CustomAction`` (``Action``,``Type``,``Target``) VALUES ('XmqrAcceptanceFailure',19,'P284 intentional rollback failure')",
  "INSERT INTO ``InstallExecuteSequence`` (``Action``,``Condition``,``Sequence``) VALUES ('XmqrAcceptanceFailure','WIX_UPGRADE_DETECTED',$($sequence + 1))"
)
foreach ($sql in $commands) { $view = $db.OpenView($sql); $view.Execute(); $view.Close() }
$summary = $db.SummaryInformation(1)
$code = '{' + [guid]::NewGuid().ToString().ToUpperInvariant() + '}'
$summary.GetType().InvokeMember('Property', [Reflection.BindingFlags]::SetProperty, $null, $summary, @(9, $code))
$summary.Persist()
$db.Commit()
""", XMQR_ACCEPTANCE_MSI=str(destination))


def installed(product):
    import winreg
    path = "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\" + product
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0,
                            winreg.KEY_READ | winreg.KEY_WOW64_64KEY):
            return True
    except FileNotFoundError:
        return False


def service_state():
    return powershell(
        """$s = Get-CimInstance Win32_Service -Filter "Name = 'xmqr-broker'" -ErrorAction Stop;
        if ($null -ne $s) { $s.State }"""
    )


def service(action):
    if action == "stop" and service_state() == "Stopped":
        return
    result = subprocess.run(["sc.exe", action, "xmqr-broker"], capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    expected = "Running" if action == "start" else "Stopped"
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if service_state() == expected:
            return
        time.sleep(.25)
    details = powershell(
        """$s = Get-CimInstance Win32_Service -Filter "Name = 'xmqr-broker'" -ErrorAction Stop;
        if ($null -ne $s) {
            $s | Select-Object State, ExitCode, ServiceSpecificExitCode | ConvertTo-Json -Compress
        }"""
    )
    raise RuntimeError(f"SCM did not reach {expected}: {details or 'service absent'}")


def assert_vm():
    if os.name != "nt" or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted" or os.environ.get("GITHUB_ACTIONS") != "true":
        raise RuntimeError("Requires a disposable GitHub-hosted Windows runner")
    if not ctypes.windll.shell32.IsUserAnAdmin():
        raise RuntimeError("Requires an elevated runner")
    signature = powershell(
        "$c = Get-CimInstance Win32_ComputerSystem; "
        "($c.Manufacturer + ' ' + $c.Model).ToLowerInvariant()"
    )
    if not any(word in signature for word in ("virtual", "vmware", "qemu", "kvm", "xen")):
        raise RuntimeError("The runner does not identify as a VM")
    if service_state():
        raise RuntimeError("Refusing to use an existing xmqr-broker service")
    products = powershell(r"""
$paths = @('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*')
Get-ItemProperty $paths -ErrorAction SilentlyContinue |
 Where-Object DisplayName -EQ 'XMQR Broker' | ForEach-Object PSChildName
"""
    )
    if products:
        raise RuntimeError("Refusing to use an existing Broker MSI installation")


def client_service(executable, data, port):
    root = data / "client-acceptance"
    root.mkdir()
    state = root / "state"
    state.mkdir()
    config = root / "client.toml"
    sink = state / "messages.ndjson"
    with sink.open("xb"):
        pass
    arguments = ["sub", "--open-lab", "--port", str(port), "--topic", "p241/retained", "--output", "jsonl"]
    config.write_text(
        "version = 1\narguments = " + json.dumps(arguments) + "\noutput_file = "
        + json.dumps(str(sink)) + "\n", encoding="utf-8",
    )
    powershell(r"""
$ErrorActionPreference = 'Stop'
foreach ($item in @(
 @{ Path=$env:XMQR_ACCEPTANCE_ROOT; Sddl='O:BAG:BAD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICI;FRFX;;;LS)' },
 @{ Path=$env:XMQR_ACCEPTANCE_STATE; Sddl='O:BAG:BAD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICI;0x1301bf;;;LS)' }
)) {
 $acl = [Security.AccessControl.DirectorySecurity]::new()
 $acl.SetSecurityDescriptorSddlForm($item.Sddl)
 Set-Acl -LiteralPath $item.Path -AclObject $acl
}
foreach ($item in @(
 @{ Path=$env:XMQR_ACCEPTANCE_CONFIG; Sddl='O:BAG:BAD:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;FR;;;LS)' },
 @{ Path=$env:XMQR_ACCEPTANCE_SINK; Sddl='O:BAG:BAD:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;0x1301bf;;;LS)' }
)) {
 $acl = [Security.AccessControl.FileSecurity]::new()
 $acl.SetSecurityDescriptorSddlForm($item.Sddl)
 Set-Acl -LiteralPath $item.Path -AclObject $acl
}
""", XMQR_ACCEPTANCE_ROOT=str(root), XMQR_ACCEPTANCE_STATE=str(state), XMQR_ACCEPTANCE_CONFIG=str(config),
       XMQR_ACCEPTANCE_SINK=str(sink))
    subprocess.run([
        "pwsh", "-NoProfile", "-NonInteractive", "-File",
        str(Path(__file__).with_name("verify_windows_component_scm.ps1")),
        "-Component", "client", "-Executable", str(executable), "-Config", str(config),
        "-DisposableVmAcceptance",
    ], check=True, timeout=180)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-msi", required=True, type=Path)
    parser.add_argument("--candidate-msi", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--client-executable", type=Path)
    parser.add_argument("--disposable-vm-acceptance", action="store_true")
    args = parser.parse_args()
    if not args.disposable_vm_acceptance:
        parser.error("Explicit --disposable-vm-acceptance is required")
    assert_vm()
    baseline = args.baseline_msi.resolve(strict=True)
    candidate = args.candidate_msi.resolve(strict=True)
    old = metadata(baseline)
    new = metadata(candidate)
    if old["version"] != "0.43.0" or new["version"] != "0.45.0" or old["product"] == new["product"]:
        raise RuntimeError("Unexpected baseline or candidate version/identity")
    data = Path(os.environ["ProgramData"]) / "XMQR" / "broker"
    if data.exists() or installed(old["product"]) or installed(new["product"]):
        raise RuntimeError("Requires a clean VM without previous Broker data")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {"result": "FAIL", "checks": [], "baseline": old, "candidate": new}

    def install(msi, label, expected=(0, 3010), remove=False):
        result = subprocess.run([
            "msiexec.exe", "/x" if remove else "/i", str(msi), "/qn", "/norestart",
            "XMQR_ACCEPT_LICENSE=1", "/l*v", str(output / (label + ".log")),
        ], timeout=180)
        if result.returncode not in expected:
            raise RuntimeError(f"{label}: msiexec returned {result.returncode}")
        return result.returncode

    def version(expected):
        binary = Path(os.environ["ProgramFiles"]) / "XMQR/Broker/mqtt-broker.exe"
        actual = subprocess.check_output([str(binary), "--version"], text=True, timeout=15).strip()
        if actual != f"mqtt-broker {expected}":
            raise RuntimeError(f"Unexpected installed binary: {actual}")

    def ready_retained(port, payload):
        deadline = time.monotonic() + 30
        while True:
            try:
                retained(port, payload)
                return
            except (OSError, RuntimeError):
                if time.monotonic() >= deadline:
                    raise
                time.sleep(.1)

    try:
        install(baseline, "baseline-install")
        if not installed(old["product"]):
            raise RuntimeError("Baseline product was not registered")
        version("0.43.0")
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        config = data / "broker.toml"
        content = f'version = 1\n[broker]\nmode = "open-lab"\nbind = "127.0.0.1:{port}"\nstate_dir = "state"\n[monitor]\nenabled = false\n'
        config.write_text(content, encoding="utf-8")
        sentinel = data / "state/upgrade-preservation.txt"
        sentinel.write_text("P284 synthetic operator data\n", encoding="utf-8")
        service("start")
        deadline = time.monotonic() + 30
        while True:
            try:
                publish(port, b"P284-before-upgrade")
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(.1)
        ready_retained(port, b"P284-before-upgrade")
        service("stop")
        shutil.copytree(data / "state", output / "backup-state")
        report["checks"].append("baseline-scm-and-persisted-retained")

        failure = output / "DO-NOT-DISTRIBUTE-failure.msi"
        prepare_failure(candidate, failure)
        failed = metadata(failure)
        install(failure, "intentional-failure", expected=(1603,))
        log = (output / "intentional-failure.log").read_text(encoding="utf-16", errors="replace")
        removal = re.search(r"Action start [^\r\n]*: RemoveExistingProducts\.", log)
        injected = re.search(r"Action start [^\r\n]*: XmqrAcceptanceFailure\.", log)
        if not removal or not injected or removal.start() >= injected.start() or "P284 intentional rollback failure" not in log:
            raise RuntimeError("Expected post-removal failure was not observed in MSI log")
        if not installed(old["product"]) or installed(failed["product"]) or installed(new["product"]):
            raise RuntimeError("MSI rollback did not restore the baseline product")
        version("0.43.0")
        if config.read_text(encoding="utf-8") != content or sentinel.read_text(encoding="utf-8") != "P284 synthetic operator data\n":
            raise RuntimeError("Rollback changed operator configuration/data")
        service("start")
        ready_retained(port, b"P284-before-upgrade")
        service("stop")
        report["checks"].append("post-removal-failure-restores-baseline-and-data")

        install(candidate, "candidate-upgrade")
        if installed(old["product"]) or not installed(new["product"]):
            raise RuntimeError("Candidate upgrade registration mismatch")
        version("0.45.0")
        if config.read_text(encoding="utf-8") != content or sentinel.read_text(encoding="utf-8") != "P284 synthetic operator data\n":
            raise RuntimeError("Upgrade changed operator configuration/data")
        service("start")
        ready_retained(port, b"P284-before-upgrade")
        if args.client_executable:
            client_service(args.client_executable.resolve(strict=True), data, port)
            report["checks"].append("paired-client-scm-start-stop")
        publish(port, b"P284-after-upgrade")
        service("stop")
        service("start")
        ready_retained(port, b"P284-after-upgrade")
        service("stop")
        report["checks"].append("upgrade-preserves-config-data-and-mqtt-after-restart")

        install(candidate, "candidate-remove", remove=True)
        install(baseline, "operational-rollback-install")
        rollback_state = data / "rollback-state"
        rollback_state.mkdir()
        powershell(r"""
$ErrorActionPreference = 'Stop'
$acl = Get-Acl -LiteralPath $env:XMQR_ACCEPTANCE_STATE
Set-Acl -LiteralPath $env:XMQR_ACCEPTANCE_ROLLBACK -AclObject $acl
""", XMQR_ACCEPTANCE_STATE=str(data / "state"), XMQR_ACCEPTANCE_ROLLBACK=str(rollback_state))
        shutil.copytree(output / "backup-state", rollback_state, dirs_exist_ok=True)
        config.write_text(content.replace('state_dir = "state"', 'state_dir = "rollback-state"'), encoding="utf-8")
        version("0.43.0")
        service("start")
        ready_retained(port, b"P284-before-upgrade")
        service("stop")
        install(baseline, "baseline-remove", remove=True)
        if service_state():
            raise RuntimeError("Broker service remained after test uninstall")
        report["checks"].append("operational-rollback-from-private-backup")
        report["result"] = "PASS"
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
    finally:
        lifecycle_log = data / "logs" / "service.log"
        if lifecycle_log.is_file():
            shutil.copyfile(lifecycle_log, output / "broker-service.log")
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
