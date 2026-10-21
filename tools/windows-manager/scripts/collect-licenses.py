"""Collect declared Windows dependency licenses without network or package changes."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

manager_root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("-o", "--output", type=Path, required=True)
parser.add_argument("--manifest-path", type=Path, default=manager_root / "Cargo.toml")
args = parser.parse_args()
manifest = args.manifest_path.resolve()
root = manifest.parent
metadata = json.loads(subprocess.check_output([
    "cargo", "metadata", "--locked", "--offline", "--format-version", "1",
    "--manifest-path", str(manifest),
    "--filter-platform", "x86_64-pc-windows-msvc",
], cwd=root))
reachable = set()
nodes = {node["id"]: node for node in metadata["resolve"]["nodes"]}
pending = [metadata["resolve"]["root"]]
while pending:
    current = pending.pop()
    if current in reachable:
        continue
    reachable.add(current)
    pending.extend(nodes[current]["dependencies"])
output = args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
rows = ["# Windows dependency notices", "", "Generated from the locked Windows dependency graph.", "",
        "Each dependency keeps its original license; these declarations do not relicense it.", "",
        "| Package | Version | Declared license |", "| --- | --- | --- |"]
missing = []
for package in sorted(metadata["packages"], key=lambda p: (p["name"], p["version"])):
    if package["id"] not in reachable or package["id"] in metadata["workspace_members"]:
        continue
    package_root = Path(package["manifest_path"]).parent
    candidates = [p for p in package_root.iterdir() if p.is_file()
                  and p.name.upper().startswith(("LICENSE", "LICENCE", "COPYING", "NOTICE", "COPYRIGHT"))]
    if package.get("license_file"):
        explicit = (package_root / package["license_file"]).resolve()
        if explicit.is_relative_to(package_root.resolve()) and explicit.is_file():
            candidates.append(explicit)
    if not candidates or not package.get("license"):
        missing.append(f"{package['name']} {package['version']}")
    destination = output / "licenses" / f"{package['name']}-{package['version']}"
    destination.mkdir(parents=True, exist_ok=True)
    for source in set(candidates):
        shutil.copy2(source, destination / source.name)
    rows.append(f"| {package['name']} | {package['version']} | {package.get('license') or 'REVIEW REQUIRED'} |")
text = "\n".join(rows) + "\n"
(output / "THIRD-PARTY-NOTICES.md").write_text(text, encoding="utf-8")
if root == manager_root:
    (root / "third-party-licenses.md").write_text(text, encoding="utf-8")
project_license = root / "LICENSE"
if not project_license.is_file() and root == manager_root:
    project_license = root.parents[1] / "LICENSE"
if not project_license.is_file() and root.name == "windows-service" and root.parent.name == "packaging":
    project_license = root.parents[1] / "LICENSE"
shutil.copy2(project_license, output / "LICENSE")
if missing:
    raise SystemExit("License source review required: " + ", ".join(missing))
print(f"Collected notices for {len(rows)-8} Windows dependency packages in {output}")
