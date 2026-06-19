"""Registra el resultado del contraste de actualizacion del temario CEF Competencias.

Tras extraer las normas citadas (extract_cef_competencias_norms.py) se constata que el
temario CEF (feb-2026) esta ACTUALIZADO: cita normativa de 2025-2026. Este script
actualiza topic_study_resources (resource_kind=temario_academia_cef) con:
  - validation_status = 'contrastado_actualizado_2026_pendiente_revision_humana'
  - notes = nota de contraste + normas sectoriales principales citadas por tema

NO es validacion juridica final (sigue requiriendo revision humana). NO toca topic_sources
ni articles. Backup antes de escribir. Dry-run por defecto; escribe con --apply.
"""
from __future__ import annotations

import argparse
import importlib.util
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "db" / "gvadicto.sqlite"
RESOURCE_KIND = "temario_academia_cef"
NEW_STATUS = "contrastado_actualizado_2026_pendiente_revision_humana"

# Decretos de estructura organica transversales (aparecen en casi todos los temas)
STRUCTURE_NORMS = {("Decreto", "16", "2025"), ("Decreto", "18", "2025"),
                   ("Decreto", "186", "2025"), ("Decreto", "9", "2026")}


def load_extractor():
    spec = importlib.util.spec_from_file_location(
        "cef_extract", str(ROOT / "scripts" / "extract_cef_competencias_norms.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def top_norms(mod, pdf: Path, n: int = 5) -> list[str]:
    text = mod.extract_text(pdf)
    norms = mod.find_norms(text)
    # exclude transversal structure decrees; sort by freq then year desc
    items = [(k, v) for k, v in norms.items() if k not in STRUCTURE_NORMS]
    items.sort(key=lambda kv: (-kv[1], -int(kv[0][2])))
    return [f"{k[0]} {k[1]}/{k[2]}" for k, _ in items[:n]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--drive-letter", default="F")
    args = ap.parse_args()

    mod = load_extractor()
    pdir = mod.pdf_dir(args.drive_letter)
    if not pdir.exists():
        raise SystemExit(f"ABORT: no existe {pdir}")

    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row

    # map topic_number -> topic_id for esp-51..60
    rows = conn.execute(
        "SELECT id, topic_number FROM topics WHERE part='especial' "
        "AND CAST(topic_number AS INTEGER) BETWEEN 51 AND 60"
    ).fetchall()
    topic_by_num = {int(r["topic_number"]): r["id"] for r in rows}

    plan = []
    for num in range(51, 61):
        pdf = pdir / f"Competencias-{num}.pdf"
        if not pdf.exists():
            print(f"  PE-{num}: PDF no encontrado, se omite")
            continue
        tops = top_norms(mod, pdf)
        topic_id = topic_by_num.get(num)
        if not topic_id:
            print(f"  PE-{num}: topic no encontrado, se omite")
            continue
        note = (
            f"Contraste 2026-06-19: temario CEF feb-2026 ACTUALIZADO (cita normativa "
            f"2025-2026, incl. Decretos estructura organica 16/2025, 18/2025, 186/2025). "
            f"Normas sectoriales principales citadas: {', '.join(tops)}. "
            f"Material de academia; requiere revision humana y verificacion de vigencia "
            f"norma-por-norma contra DOGV/BOE."
        )
        plan.append((topic_id, num, note))

    print(f"=== Actualizaciones a aplicar: {len(plan)} ===")
    for topic_id, num, note in plan:
        print(f"  PE-{num} (topic_id={topic_id}): {note[:90]}...")

    if not args.apply:
        print("\n=== DRY-RUN (sin escritura). Usa --apply. ===")
        conn.close()
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = ROOT / "db" / f"gvadicto.backup_pre_cef_contraste_{ts}.sqlite"
    shutil.copy2(DB, backup)
    print(f"\n  Backup: {backup.name}")

    now = datetime.now().isoformat(timespec="seconds")
    updated = 0
    for topic_id, num, note in plan:
        cur = conn.execute(
            "UPDATE topic_study_resources SET validation_status=?, notes=?, updated_at=? "
            "WHERE topic_id=? AND resource_kind=?",
            (NEW_STATUS, note, now, topic_id, RESOURCE_KIND),
        )
        updated += cur.rowcount
    conn.commit()
    print(f"  Filas actualizadas: {updated}")
    conn.close()
    print("\n=== APPLY completado. ===")


if __name__ == "__main__":
    main()
