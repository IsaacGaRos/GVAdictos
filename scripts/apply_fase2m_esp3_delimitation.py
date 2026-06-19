"""Fase 2M: cierre de esp-3 (id=18) — Administracion como persona juridica, potestades,
discrecionalidad y su control, conflictos de jurisdiccion.

Fuentes (ya importadas; se vinculan por ser las correctas, aunque el fallback inicial solo
tenia LOPJ + LO 2/1987 sin articulos):
  - LRJSP (law 4): art 3 (principios; personalidad juridica unica), art 4 (principios de
    intervencion = potestades administrativas).
  - LJCA (law 51): control jurisdiccional de la Administracion y de la discrecionalidad
    (arts 1, 25, 70, 71, 106).
  - LOPJ (law 37): conflictos de jurisdiccion y de competencia (arts 38, 39, 41, 42, 43, 44).

Garantias: dry-run por defecto; backup; no toca articles/parser/importer; no borra mappings
ajenos; aborta si esp-3 ya tiene mapping fino ajeno.
"""
from __future__ import annotations
import argparse, shutil, sqlite3, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "db" / "gvadicto.sqlite"
TOPIC_ID = 18
MAPPING_BASIS = "delimitacion_fina_claude_fase2m_esp3_2026_06_19"
VALIDATION_STATUS = "validado_fuente_oficial_pendiente_revision_humana"
LAW_LABEL = {4: "Ley 40/2015", 51: "Ley 29/1998 (LJCA)", 37: "LOPJ"}

PLAN = [  # (law_id, ref, priority, note)
    (4, "3", "alta", "esp-3 LRJSP: principios; personalidad juridica unica de cada Administracion"),
    (4, "4", "media", "esp-3 LRJSP: principios de intervencion (potestades administrativas)"),
    (51, "1", "alta", "esp-3 LJCA: ambito del control contencioso-administrativo"),
    (51, "25", "media", "esp-3 LJCA: actividad administrativa impugnable"),
    (51, "70", "alta", "esp-3 LJCA: sentencia; control de la actuacion administrativa"),
    (51, "71", "alta", "esp-3 LJCA: alcance de la estimacion (control de la discrecionalidad)"),
    (51, "106", "baja", "esp-3 LJCA: ejecucion de sentencias contra la Administracion"),
    (37, "38", "alta", "esp-3 LOPJ: conflictos de jurisdiccion Administracion-Tribunales"),
    (37, "39", "media", "esp-3 LOPJ: conflictos de jurisdiccion (organo competente)"),
    (37, "41", "media", "esp-3 LOPJ: tramitacion de los conflictos de jurisdiccion"),
    (37, "42", "media", "esp-3 LOPJ: conflictos de competencia entre ordenes jurisdiccionales"),
    (37, "43", "baja", "esp-3 LOPJ: conflictos de competencia (regimen)"),
    (37, "44", "baja", "esp-3 LOPJ: preferencia del orden penal"),
]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    conn = sqlite3.connect(str(DB)); conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        row = conn.execute("SELECT topic_number, part FROM topics WHERE id=?", (TOPIC_ID,)).fetchone()
        if not row or int(row["topic_number"]) != 3 or row["part"] != "especial":
            raise SystemExit(f"ABORT: topic_id={TOPIC_ID} no es esp-3")
        foreign = conn.execute("SELECT COUNT(*) FROM topic_sources WHERE topic_id=? AND article_id IS NOT NULL AND mapping_basis<>?",
                               (TOPIC_ID, MAPPING_BASIS)).fetchone()[0]
        if foreign:
            raise SystemExit(f"ABORT: esp-3 ya tiene mapping fino ajeno ({foreign})")
        resolved = []
        for law_id, ref, prio, note in PLAN:
            r = conn.execute("SELECT id FROM articles WHERE law_id=? AND article_ref=?", (law_id, ref)).fetchone()
            if not r:
                raise SystemExit(f"ABORT: {LAW_LABEL[law_id]} art {ref} no existe")
            resolved.append((law_id, int(r["id"]), ref, prio, note))
        print(f"=== esp-3: {len(resolved)} articulos resueltos ===")
        for law_id, aid, ref, prio, note in resolved:
            print(f"  {LAW_LABEL[law_id]:>18} art {ref:>3} -> id={aid} [{prio}]")
        if not args.apply:
            print("\n=== DRY-RUN OK. Usa --apply. ==="); return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(DB, ROOT / "db" / f"gvadicto.backup_pre2m_esp3_{ts}.sqlite")
        conn.execute("DELETE FROM topic_sources WHERE topic_id=? AND mapping_basis=?", (TOPIC_ID, MAPPING_BASIS))
        for law_id, aid, ref, prio, note in resolved:
            conn.execute("""INSERT INTO topic_sources(topic_id, law_id, article_id, normative_reference,
                coverage_status, mapping_basis, priority, validation_status, notes) VALUES (?,?,?,?,?,?,?,?,?)""",
                (TOPIC_ID, law_id, aid, f"{LAW_LABEL[law_id]} art. {ref}", "articulo_delimitado",
                 MAPPING_BASIS, prio, VALIDATION_STATUS, note))
        conn.commit()
        broken = conn.execute("SELECT COUNT(*) FROM topic_sources WHERE article_id IS NOT NULL AND article_id NOT IN (SELECT id FROM articles)").fetchone()[0]
        if broken:
            conn.rollback(); raise SystemExit(f"ABORT: {broken} FK rotas")
        total = conn.execute("SELECT COUNT(*) FROM topic_sources").fetchone()[0]
        print(f"\n  Insertadas: {len(resolved)} | topic_sources: {total} | FK rotas: {broken}")
        print("=== APPLY OK. ===")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
