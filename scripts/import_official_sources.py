from __future__ import annotations

import csv
import re
import sys
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.laws.importer import import_law


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed" / "official_sources"


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)

    def text(self) -> str:
        return "\n".join(self.parts)


class ElementTextExtractor(HTMLParser):
    def __init__(self, target_id: str) -> None:
        super().__init__()
        self.target_id = target_id
        self.depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_by_name = dict(attrs)
        if attrs_by_name.get("id") == self.target_id:
            self.depth = 1
            return
        if self.depth:
            self.depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self.depth:
            self.depth -= 1

    def handle_data(self, data: str) -> None:
        if self.depth:
            text = data.strip()
            if text:
                self.parts.append(text)

    def text(self) -> str:
        return "\n".join(self.parts)


def pdf_to_text(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def html_to_text(path: Path) -> str:
    raw_html = path.read_text(encoding="utf-8", errors="ignore")
    document_parser = ElementTextExtractor("document1")
    document_parser.feed(raw_html)
    text = document_parser.text()
    if not text:
        parser = TextExtractor()
        parser.feed(raw_html)
        text = parser.text()
    text = unescape(text)
    return re.sub(r"\n{3,}", "\n\n", text)


def convert_to_text(path: Path, mime_type: str) -> str:
    if mime_type == "application/pdf" or path.suffix.lower() == ".pdf":
        return pdf_to_text(path)
    if "html" in mime_type or path.suffix.lower() in {".html", ".htm"}:
        return html_to_text(path)
    return path.read_text(encoding="utf-8", errors="ignore")


def iter_manifests(paths: list[Path]):
    for manifest in paths:
        with manifest.open("r", encoding="utf-8-sig", newline="") as fh:
            yield from csv.DictReader(fh)


def main() -> None:
    manifests = [
        ROOT / "data" / "sources" / "official_normative_sources_seed.csv",
        ROOT / "data" / "sources" / "official_normative_sources_extra.csv",
        ROOT / "data" / "sources" / "official_normative_sources_a1_topic_validation.csv",
        ROOT / "data" / "sources" / "official_normative_sources_a1_autentica_supplemental.csv",
        ROOT / "data" / "sources" / "official_normative_sources_eurlex.csv",
    ]
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    imported = 0
    for row in iter_manifests([path for path in manifests if path.exists()]):
        if row.get("status") not in {"descargado", "downloaded"}:
            continue
        source_path = ROOT / row["path"]
        if not source_path.exists():
            print(f"SKIP missing: {source_path}")
            continue
        text_path = PROCESSED_DIR / f"{row['external_id']}.txt"
        text_path.write_text(convert_to_text(source_path, row.get("mime_type", "")), encoding="utf-8")
        law_id = import_law(text_path, row["title"], original_source_path=source_path)
        print(f"{law_id}: {row['title']}")
        imported += 1
    print(f"Fuentes oficiales importadas: {imported}")


if __name__ == "__main__":
    main()
