#!/usr/bin/env python3
"""P261 integration gate. Privileged containers ONLY on disposable GitHub-hosted runners."""
import argparse
import json
import os
import pathlib
import subprocess
import time
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]


def run(command, expected=0, timeout=600):
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    if result.returncode != expected:
        print(result.stdout[-10000:])
        print(result.stderr[-10000:])
        raise RuntimeError(f"exit{result.returncode}, esperado{expected}: {command[:3]}")
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=["fresh", "bridge-resume", "mqtt-resume"], required=True)
    parser.add_argument("--report", type=pathlib.Path, required=True)
    args = parser.parse_args()
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted":
        raise SystemExit("Gate privilegiado restrito a runner GitHub hospedado descartavel; nao executar no host do operador.")
    name = "xmqr-installer-ci-" + uuid.uuid4().hex[:12]
    image = "xmqr-installer-ci:" + uuid.uuid4().hex[:12]
    report = {"source_revision": os.environ["GITHUB_SHA"], "scenario": args.scenario,
              "platform": "Ubuntu26 amd64 systemd disposable container", "status": "FAIL"}
    container_id = None
    try:
        run(["docker", "build", "-f", str(ROOT/"packaging/oracle-installer/Dockerfile.ci"),
             "-t", image, str(ROOT/"packaging/oracle-installer")])
        container_id = run(["docker", "run", "-d", "--name", name, "--privileged", "--cgroupns=host",
                            "--tmpfs", "/run", "--tmpfs", "/run/lock", "--tmpfs", "/tmp",
                            "-v", "/sys/fs/cgroup:/sys/fs/cgroup:rw", "-v", f"{ROOT}:/work:ro", image])
        def execute(*command, expected=0):
            return run(["docker", "exec", container_id, *command], expected=expected)
        for _ in range(60):
            status = subprocess.run(["docker", "exec", container_id, "systemctl", "is-system-running"],
                                    capture_output=True, text=True).stdout.strip()
            if status in {"running", "degraded"}:
                break
            time.sleep(1)
        else:
            raise RuntimeError("systemd nao iniciou")
        execute("bash", "-n", "/work/scripts/install_oracle_x86.sh")
        execute("bash", "/work/scripts/install_oracle_x86.sh", "--version")
        fixture = r'''
import pathlib, shutil, sys
directory=pathlib.Path('/tmp/xmqr-legacy-fixture'); directory.mkdir(mode=0o700)
source=pathlib.Path('/work/scripts/install_oracle_x86.sh').read_text()
if sys.argv[1]=='bridge-resume':
    old="== 'mqtt-bridge 0.5.0 (xmqr-client 0.43.0)'"
    assert source.count(old)==1
    source=source.replace(old,"== 'mqtt-bridge 0.5.0'",1)
else:
    old='--client-id p260-valid-after '
    assert source.count(old)==1
    source=source.replace(old,'--client-id p260-valid-after-negative ',1)
    check='python3 "$verifier" --script "$(readlink -f -- "$0")"'
    assert source.count(check)==1
    source=source.replace(check,': # legacy fixture predates CLI preflight',1)
(directory/'install_oracle_x86.sh').write_text(source)
shutil.copyfile('/work/scripts/verify_oracle_installer.py',directory/'verify_oracle_installer.py')
'''
        materials = r'''
import hashlib,json,os,pathlib,sys
os.umask(0o077)
paths=['/root/xmqr-oracle-pki/ca.key','/root/xmqr-oracle-pki/server.key',
       '/root/xmqr-oracle-pki/client.key','/etc/xmqr/server.key',
       '/etc/xmqr-client/oracle/client.key','/etc/xmqr-client/oracle/password',
       '/etc/xmqr-admin/access.token','/etc/xmqr/security.toml']
values={p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in paths}
checkpoint=pathlib.Path('/tmp/xmqr-material-digests.json')
if sys.argv[1]=='save': checkpoint.write_text(json.dumps(values))
else:
    assert values==json.loads(checkpoint.read_text()),'materiais privados foram alterados'
    print('MATERIALS_PRESERVED')
'''
        if args.scenario == "fresh":
            output = execute("bash", "/work/scripts/install_oracle_x86.sh", "1.1.1.1")
        else:
            execute("python3", "-c", fixture, args.scenario)
            legacy = subprocess.run(["docker", "exec", container_id, "bash",
                                     "/tmp/xmqr-legacy-fixture/install_oracle_x86.sh", "1.1.1.1"],
                                    capture_output=True, text=True, timeout=600)
            if args.scenario == "bridge-resume":
                assert legacy.returncode == 1 and "Versao inesperada da bridge" in legacy.stderr, legacy.stderr[-3000:]
                mode = "--resume-packages"
            else:
                assert legacy.returncode == 2 and "--client-id deve ter 1 a 23" in legacy.stderr, legacy.stderr[-3000:]
                execute("python3", "-c", materials, "save")
                mode = "--resume-mqtt"
            output = execute("bash", "/work/scripts/install_oracle_x86.sh", mode, "1.1.1.1")
            report["legacy_failure_reproduced"] = True
            if args.scenario == "mqtt-resume":
                execute("python3", "-c", materials, "check")
                report["private_materials_preserved"] = True
        assert "XMQR_INSTALL_PASS" in output, output[-3000:]
        report["installer_pass"] = True
        execute("systemctl", "is-active", "xmqr-broker.service", "xmqr-client-sub@oracle.service", "xmqr-admin.service")
        execute("curl", "--noproxy", "*", "--fail", "--silent", "http://127.0.0.1:9090/ready")
        before = execute("cat", "/var/lib/xmqr-oracle-install/status")
        refused = subprocess.run(["docker", "exec", container_id, "bash", "/work/scripts/install_oracle_x86.sh",
                                  "--resume-mqtt", "1.1.1.1"], capture_output=True, text=True, timeout=30)
        assert refused.returncode != 0 and "checkpoint" in refused.stderr, refused.stderr
        assert before == execute("cat", "/var/lib/xmqr-oracle-install/status")
        execute("systemctl", "is-active", "xmqr-broker.service", "xmqr-client-sub@oracle.service", "xmqr-admin.service")
        report["wrong_checkpoint_refused_without_mutation"] = True
        report["status"] = "PASS"
    finally:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, sort_keys=True, indent=2)+"\n")
        if container_id:
            subprocess.run(["docker", "rm", "--force", container_id], capture_output=True)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
