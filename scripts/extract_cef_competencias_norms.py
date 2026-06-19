"""Extrae las referencias normativas citadas en el temario CEF de Competencias (PE-51..60).

Objetivo:
  - Contrastar que el temario CEF este actualizado: listar las normas (ley/decreto)
    que cita cada tema y cruzarlas con las leyes ya importadas en la BD.
  - Identificar normas sectoriales que faltan por importar (bloquearon la Fase 2K).

NO escribe en la BD. Solo lee los PDF de Drive y genera un informe.

Uso:
  python scripts/extract_cef_competencias_norms.py
  python scripts/extract_cef_competencias_norms.py --drive-letter F
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "db" / "gvadicto.sqlite"
REPORTS = ROOT / "reports"

# Norma reference patterns (Spanish legal citations)
NORM_RE = re.compile(
    r"\b("
    r"Ley\s+Org[aá]nica|"
    r"Real\s+Decreto\s+Legislativo|"
    r"Real\s+Decreto-ley|"
    r"Real\s+Decreto|"
    r"Decreto\s+Legislativo|"
    r"Decreto-ley|"
    r"Decreto\s+ley|"
    r"Decreto|"
    r"Ley"
    r")\s+(\d+)\s*/\s*(\d{4})",
    re.IGNORECASE,
)


def pdf_dir(letter: str) -> Path:
    return Path(
        f"{letter}:\\Mi unidad\\Opo\\EraCEF\\TemarioAulaVirtualCompleto"
        f"\\Especial\\6- Competencias"
    )


def extract_text(path: Path) -> str:
    import pdfplumber
    parts = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts)


def normalize_kind(kind: str) -> str:
    k = kind.lower().replace("-", " ").replace("  ", " ").strip()
    mapping = {
        "ley organica": "Ley Organica",
        "ley orgánica": "Ley Organica",
        "real decreto legislativo": "Real Decreto Legislativo",
        "real decreto ley": "Real Decreto-ley",
        "real decreto": "Real Decreto",
        "decreto legislativo": "Decreto Legislativo",
        "decreto ley": "Decreto-ley",
        "decreto": "Decreto",
        "ley": "Ley",
    }
    return mapping.get(k, kind)


def find_norms(text: str) -> dict[tuple[str, str, str], int]:
    found: dict[tuple[str, str, str], int] = {}
    for m in NORM_RE.finditer(text):
        kind = normalize_kind(m.group(1))
        num, year = m.group(2), m.group(3)
        key = (kind, num, year)
        found[key] = found.get(key, 0) + 1
    return found


def load_db_laws() -> list[tuple[str, str]]:
    """Return (num, year) pairs roughly identifiable from laws.name."""
    conn = sqlite3.connect(str(DB))
    rows = conn.execute("SELECT name FROM laws").fetchall()
    conn.close()
    pairs = []
    for (name,) in rows:
        for m in re.finditer(r"(\d+)\s*[/-]\s*(\d{4})", name or ""):
            pairs.append((m.group(1), m.group(2)))
    return pairs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--drive-letter", default="F", help="Letra de unidad de Google Drive")
    args = ap.parse_args()

    d = pdf_dir(args.drive_letter)
    if not d.exists():
        raise SystemExit(f"ABORT: no existe la carpeta {d}. Verifica la letra de Drive.")

    db_pairs = set(load_db_laws())
    REPORTS.mkdir(exist_ok=True)
    report_lines = ["# Contraste temario CEF Competencias — normas citadas", ""]

    topic_map = {n: n for n in range(51, 61)}
    for num in sorted(topic_map):
        pdf = d / f"Competencias-{num}.pdf"
        if not pdf.exists():
            report_lines.append(f"## PE-{num}: PDF NO ENCONTRADO\n")
            print(f"PE-{num}: PDF NO ENCONTRADO")
            continue
        text = extract_text(pdf)
        norms = find_norms(text)
        # Sort by frequency desc then year desc
        ordered = sorted(norms.items(), key=lambda kv: (-kv[1], -int(kv[0][2])))

        print(f"\n=== PE-{num} ({len(norms)} normas distintas, {len(text)} chars) ===")
        report_lines.append(f"## PE-{num} — {len(norms)} normas distintas citadas")
        report_lines.append("")
        report_lines.append("| Norma | Veces | En BD |")
        report_lines.append("| --- | ---: | :---: |")
        for (kind, n, y), cnt in ordered:
            in_db = "si" if (n, y) in db_pairs else "-"
            line = f"{kind} {n}/{y}"
            print(f"  {line:<32} x{cnt:<3} {'[BD]' if in_db=='si' else ''}")
            report_lines.append(f"| {line} | {cnt} | {in_db} |")
        report_lines.append("")

    out = REPORTS / "cef_competencias_normas_citadas.md"
    out.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"\nInforme: {out}")


if __name__ == "__main__":
    main()
