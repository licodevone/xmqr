"""P77: conferir código mostrado, links e arquivos dos pacotes didáticos."""

from html.parser import HTMLParser
import json
from pathlib import Path
import zipfile

from build_first_commit_course import OUTPUT, original_files, snapshots


class Guide(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids, self.links, self.files, self.details = set(), [], {}, []
        self.current, self.in_row, self.cell, self.in_code = None, False, 0, False
        self.text = ""

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "id" in values:
            if values["id"] in self.ids:
                raise ValueError("ID duplicado no guia")
            self.ids.add(values["id"])
        if tag == "a" and "href" in values:
            self.links.append(values["href"])
        if tag == "details":
            self.details.append(self.current)
            if "code-file" in values.get("class", ""):
                stage = values["id"].split("-")[1]
                self.current = (stage, values["data-path"])
                self.files[self.current] = []
        if tag == "tr" and "data-line" in values:
            self.in_row, self.cell, self.text = True, 0, ""
        if tag == "td" and self.in_row:
            self.cell += 1
        if tag == "code" and self.in_row and self.cell == 2:
            self.in_code = True

    def handle_data(self, data):
        if self.in_code:
            self.text += data

    def handle_endtag(self, tag):
        if tag == "code":
            self.in_code = False
        if tag == "tr" and self.in_row:
            self.files[self.current].append(self.text)
            self.in_row = False
        if tag == "details":
            self.current = self.details.pop()


def verify():
    guide = Guide()
    guide.feed((OUTPUT / "index.html").read_text(encoding="utf-8"))
    for link in guide.links:
        if "://" in link:
            continue
        if link.startswith("#"):
            if link != "#" and link[1:] not in guide.ids:
                raise ValueError(f"Âncora ausente: {link}")
        elif not (OUTPUT / link).is_file():
            raise ValueError(f"Arquivo de link ausente: {link}")
    original = original_files()
    previous, line_count = {}, 0
    expected_tables = set()
    for stage, title, files, order, concepts in snapshots(original):
        for name, data in files.items():
            if data != previous.get(name) and (name.endswith(".rs") or name == "Cargo.toml"):
                key = (stage, name)
                expected_tables.add(key)
                if guide.files[key] != data.decode().splitlines():
                    raise ValueError(f"Código exibido difere da fonte: {key}")
                if name.endswith(".rs"):
                    line_count += len(guide.files[key])
        previous = files
    if set(key for key, value in guide.files.items() if value) != expected_tables:
        raise ValueError("Tabela de fonte incompleta ou adicional")
    if previous != original:
        raise ValueError("R10 difere do histórico")
    for item in json.loads((OUTPUT / "indice.json").read_text(encoding="utf-8")):
        with zipfile.ZipFile(OUTPUT / item["zip"]) as archive:
            if archive.testzip():
                raise ValueError("CRC de etapa inválido")
    with zipfile.ZipFile(OUTPUT / "primeiro-commit-curso-completo.zip") as archive:
        if archive.testzip():
            raise ValueError("CRC de pacote completo inválido")
        if archive.read("index.html") != (OUTPUT / "index.html").read_bytes():
            raise ValueError("Guia empacotado desatualizado")
    print(f"PASS guia: {line_count} linhas Rust exibidas fielmente; links/âncoras únicos; R10 Git exato; onzeZIPs íntegros")


if __name__ == "__main__":
    verify()
