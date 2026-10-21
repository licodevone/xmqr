# SPDX-License-Identifier: MIT
"""Validate installer contracts; optional WiX fixture builds never install software."""
from __future__ import annotations

import argparse
import base64
import copy
from pathlib import Path
import shutil
import subprocess
import tempfile
import tomllib
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
PACKAGING = ROOT / "packaging" / "windows"
NS = {"w": "http://wixtoolset.org/schemas/v4/wxs"}
WIX = False


class PackagingContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.product = ET.parse(PACKAGING / "Product.wxs")
        cls.manager = ET.parse(PACKAGING / "Manager.wxs")

    def test_services_are_limited_account_and_not_started_by_install(self):
        service = self.product.find(".//w:ServiceInstall", NS)
        self.assertEqual(service.attrib["Account"], r"NT AUTHORITY\LocalService")
        self.assertEqual(service.attrib["Start"], "auto")
        self.assertEqual(service.attrib["Type"], "ownProcess")
        self.assertIn('--config "[DATADIR]$(var.ConfigName)"', service.attrib["Arguments"])
        control = self.product.find(".//w:ServiceControl", NS)
        self.assertNotIn("Start", control.attrib)
        self.assertEqual(control.attrib["Stop"], "both")
        self.assertEqual(control.attrib["Remove"], "uninstall")
        self.assertEqual(control.attrib["Wait"], "yes")

    def test_registration_is_machine_wide_and_component_specific(self):
        registration = self.product.find(".//w:Component[@Id='TrayRegistration']", NS)
        self.assertEqual(registration.attrib["Bitness"], "always64")
        key = registration.find("w:RegistryKey", NS)
        self.assertEqual(key.attrib["Root"], "HKLM")
        self.assertEqual(key.attrib["Key"], r"SOFTWARE\XMQR\Components\$(var.ComponentId)")
        self.assertEqual(key.attrib["ForceDeleteOnUninstall"], "yes")
        values = {value.attrib["Name"]: value.attrib["Value"] for value in key}
        self.assertEqual(values["Executable"], "[#MainExecutableFile]")
        self.assertEqual(values["ConfigFile"], "[DATADIR]$(var.ConfigName)")
        self.assertEqual(values["CertificatesDir"], "[CERTSDIR]")
        self.assertEqual(values["LogsDir"], "[LOGSDIR]")

    def test_configuration_and_data_survive_uninstall_and_upgrade(self):
        configuration = self.product.find(".//w:Component[@Id='InitialConfiguration']", NS)
        self.assertEqual(configuration.attrib["Permanent"], "yes")
        self.assertEqual(configuration.attrib["NeverOverwrite"], "yes")
        for identifier in (
            "PrivateDataDirectory", "PrivateCertificatesDirectory",
            "PrivateLogsDirectory", "PrivateStateDirectory",
        ):
            component = self.product.find(f".//w:Component[@Id='{identifier}']", NS)
            self.assertEqual(component.attrib["Permanent"], "yes")
            self.assertIsNotNone(component.find("w:RegistryValue[@KeyPath='yes']", NS))
        self.assertFalse(self.product.findall(".//w:RemoveFile", NS))
        previous = self.product.find(".//w:Property[@Id='DATADIR']/w:RegistrySearch", NS)
        self.assertEqual(previous.attrib["Name"], "DataDirectory")
        self.assertEqual(previous.attrib["Bitness"], "always64")

    def test_private_directories_do_not_grant_everyone_or_users_access(self):
        permissions = self.product.findall(".//w:CreateFolder/w:PermissionEx", NS)
        self.assertEqual(len(permissions), 4)
        for permission in permissions:
            sddl = permission.attrib["Sddl"]
            self.assertTrue(sddl.startswith("D:P"))
            self.assertIn("(A;OICI;FA;;;SY)", sddl)
            self.assertIn("(A;OICI;FA;;;BA)", sddl)
            self.assertNotIn(";;;WD)", sddl)
            self.assertNotIn(";;;BU)", sddl)
        for identifier in ("PrivateDataDirectory", "PrivateCertificatesDirectory"):
            element = self.product.find(f".//w:Component[@Id='{identifier}']/w:CreateFolder/w:PermissionEx", NS)
            self.assertIn("(A;OICI;FRFX;;;LS)", element.attrib["Sddl"])

    def test_shared_tray_survives_component_removal(self):
        self.assertIsNone(self.product.find(".//w:RegistryValue[@Name='XMQR Manager']", NS))
        startup = self.manager.find(".//w:RegistryValue[@Name='XMQR Manager']", NS)
        self.assertEqual(startup.attrib["Root"], "HKLM")
        self.assertEqual(startup.attrib["Value"], '"[#ManagerExecutableFile]"')
        self.assertFalse(self.manager.findall(".//w:ServiceInstall", NS))
        self.assertFalse(self.manager.findall(".//w:CustomAction", NS))
        self.assertFalse(self.product.findall(".//w:CustomAction", NS))

    def test_arbitrary_acl_paths_and_duplicate_same_version_are_rejected(self):
        conditions = [item.attrib["Condition"] for item in self.product.findall(".//w:Launch", NS)]
        for name in ("DATADIR", "LOGSDIR", "CERTSDIR", "STATEDIR"):
            self.assertTrue(any(f"NOT {name} OR {name} = XmqrExpected" in value for value in conditions))
        setters = self.product.findall(".//w:SetProperty", NS)
        self.assertEqual(len(setters), 4)
        for setter in setters:
            self.assertTrue(setter.attrib["Value"].startswith("[CommonAppDataFolder]XMQR\\$(var.ComponentId)\\"))
            self.assertEqual(setter.attrib["Before"], "LaunchConditions")
            self.assertEqual(setter.attrib["Sequence"], "both")
        for document in (self.product, self.manager):
            match = document.find(".//w:UpgradeVersion[@Property='XMQR_SAME_VERSION']", NS)
            self.assertEqual(match.attrib["Minimum"], match.attrib["Maximum"])
            self.assertEqual(match.attrib["OnlyDetect"], "yes")
            self.assertIsNotNone(document.find(".//w:Launch[@Condition='Installed OR NOT XMQR_SAME_VERSION']", NS))

    def check_service_manifest(self, repository):
        if not repository.is_dir():
            self.skipTest(f"NOT_PRESENT: optional sibling {repository.name}")
        normal_manifest = repository / "Cargo.toml"
        service_manifest = repository / "packaging/windows-service/Cargo.toml"
        with normal_manifest.open("rb") as file:
            normal = tomllib.load(file)
        with service_manifest.open("rb") as file:
            service = tomllib.load(file)
        for field in ("name", "version", "edition", "rust-version"):
            self.assertEqual(normal["package"][field], service["package"][field], field)
        for section in ("dependencies", "dev-dependencies"):
            self.assertEqual(normal.get(section, {}), service.get(section, {}), section)
        targets = copy.deepcopy(service.get("target", {}))
        self.assertEqual(targets['cfg(windows)']["dependencies"].pop("windows-service"), "0.8")
        if not targets['cfg(windows)']["dependencies"]:
            targets.pop('cfg(windows)')
        self.assertEqual(normal.get("target", {}), targets)
        def normalized_patches(document, base):
            patches = copy.deepcopy(document.get("patch", {}))
            for source in patches.values():
                for entry in source.values():
                    if isinstance(entry, dict) and "path" in entry:
                        entry["path"] = str((base / entry["path"]).resolve())
            return patches
        self.assertEqual(normalized_patches(normal, repository), normalized_patches(service, service_manifest.parent))
        self.assertIn("windows-service-runtime", service["features"]["default"])
        self.assertEqual((service_manifest.parent / service["bin"][0]["path"]).resolve(), repository / "src/main.rs")

    def test_broker_service_manifest_does_not_drift(self):
        self.check_service_manifest(ROOT)

    def test_client_service_manifest_does_not_drift(self):
        self.check_service_manifest(ROOT.parent / "xmqr-client")

    def test_admin_service_manifest_does_not_drift(self):
        self.check_service_manifest(ROOT.parent / "xmqr-admin")

    def test_defaults_remain_loopback_and_unprovisioned(self):
        with (PACKAGING / "broker.toml").open("rb") as file:
            broker = tomllib.load(file)
        self.assertEqual(broker["broker"]["mode"], "secure-mtls")
        self.assertEqual(broker["broker"]["bind"], "127.0.0.1:8883")
        self.assertEqual(broker["tls"]["server_key"], "certificates/server.key")
        with (PACKAGING / "client.toml").open("rb") as file:
            self.assertEqual(tomllib.load(file)["arguments"], [])
        with (PACKAGING / "admin.toml").open("rb") as file:
            admin = tomllib.load(file)
        self.assertEqual(admin["bind"], "127.0.0.1:9080")
        self.assertEqual(admin["token_file"], "token")

    def test_build_and_install_powershell_parse(self):
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if not powershell:
            self.skipTest("BLOCKED: PowerShell parser unavailable")
        for name in ("build-windows.ps1", "install-windows.ps1"):
            path = str(ROOT / "scripts" / name).replace("'", "''")
            script = (
                "$errors = $null; "
                f"[System.Management.Automation.Language.Parser]::ParseFile('{path}',"
                "[ref]$null,[ref]$errors) | Out-Null; "
                "if ($errors.Count) { $errors | ConvertTo-Json; exit 1 }"
            )
            encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
            result = subprocess.run(
                [powershell, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_wix_schema_and_linkage_fixtures(self):
        if not WIX:
            self.skipTest("NOT_RUN: use --wix for schema-only fixture builds")
        wix = shutil.which("wix")
        self.assertIsNotNone(wix, "BLOCKED: WiX executable unavailable")
        # Explicit disposable fixture. No product .exe is used or represented as built.
        fixture_root = (ROOT / "target" / "windows-packaging-tests").resolve()
        fixture_root.mkdir(parents=True, exist_ok=True)
        self.assertTrue(fixture_root.is_relative_to(ROOT.resolve()))
        temporary = tempfile.TemporaryDirectory(prefix="xmqr-wix-fixture-", dir=fixture_root)
        directory = Path(temporary.name).resolve()
        self.assertTrue(directory.is_relative_to(fixture_root))
        try:
            (directory / "xmqr-manager.exe").write_bytes(b"NOT AN EXECUTABLE: schema validation fixture")
            (directory / "component.exe").write_bytes(b"NOT AN EXECUTABLE: schema validation fixture")
            notices = directory / "notices"
            notices.mkdir()
            (notices / "LICENSE").write_text("SCHEMA FIXTURE LICENSE", encoding="utf-8")
            for kind in ("broker", "client", "admin"):
                component = "client-default" if kind == "client" else kind
                arguments = [
                    wix, "build", str(PACKAGING / "Product.wxs"), "-arch", "x64",
                    "-d", "ProductName=SCHEMA FIXTURE ONLY - DO NOT INSTALL",
                    "-d", "ProductVersion=0.0.0",
                    "-d", "UpgradeCode=AC7BFB24-F1C0-4536-AB9F-89F758F25DBB",
                    "-d", f"ProductFolder={kind}", "-d", f"BinaryDir={directory}",
                    "-d", "ExecutableName=component.exe", "-d", f"ComponentId={component}",
                    "-d", f"Kind={kind}", "-d", f"ServiceName=xmqr-{component}",
                    "-d", f"ConfigName={kind}.toml", "-d", f"ConfigSource={PACKAGING / (kind + '.toml')}",
                    "-d", f"NoticesDir={notices}",
                    "-out", str(directory / f"fixture-{kind}.msi"),
                ]
                result = subprocess.run(arguments, capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([
                wix, "build", str(PACKAGING / "Manager.wxs"), "-arch", "x64",
                "-d", "ProductVersion=0.0.0", "-d", f"BinaryDir={directory}",
                "-d", f"NoticesDir={notices}",
                "-out", str(directory / "fixture-manager.msi"),
            ], capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        finally:
            # Deletion is restricted to the verified dedicated temporary directory.
            temporary.cleanup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wix", action="store_true")
    options = parser.parse_args()
    WIX = options.wix
    unittest.main(argv=["verify_windows_packaging.py"], verbosity=2)
