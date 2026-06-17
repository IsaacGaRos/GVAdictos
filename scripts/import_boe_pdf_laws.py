from __future__ import annotations

import csv
import sys
from pathlib import Path

from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.laws.importer import import_law


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed" / "leyes_boe"


def pdf_to_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def main() -> None:
    manifest_path = ROOT / "data" / "sources" / "official_normative_sources_seed.csv"
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    imported = 0
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if row["status"] != "descargado" or row["source_kind"] != "boe_consolidado":
                continue
            pdf_path = ROOT / row["path"]
            text_path = PROCESSED_DIR / f"{row['external_id']}.txt"
            text_path.write_text(pdf_to_text(pdf_path), encoding="utf-8")
            law_id = import_law(text_path, row["title"], original_source_path=pdf_path)
            print(f"{law_id}: {row['title']}")
            imported += 1
    print(f"Leyes BOE importadas: {imported}")


if __name__ == "__main__":
    main()
