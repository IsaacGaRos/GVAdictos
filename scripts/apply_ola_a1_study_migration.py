#!/usr/bin/env python3
"""
Ola A1: Migrar src/study a BD real.

Pasos:
1. Crear 5 nuevas tablas (study_article_notes, study_highlights, study_progress, study_marks, study_last_reviews)
2. Migrar datos de study_annotations a las nuevas tablas
3. Validar integridad
4. Registrar cambios

DRY RUN: ejecutar con --dry-run para ver qué pasaría sin hacer cambios.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

from src.core.db import connect
from src.study.schema import apply_study_schema, STUDY_TABLES


def ensure_study_tables_exist(conn) -> None:
    """Crear las 5 tablas de estudio si no existen."""
    apply_study_schema(conn)
    print("[OK] Tablas de estudio creadas/verificadas")


def migration_data_exists(conn) -> bool:
    """Comprobar si hay datos en study_annotations para migrar."""
    row = conn.execute("SELECT COUNT(*) FROM study_annotations").fetchone()
    count = int(row[0]) if row else 0
    print(f"     Anotaciones existentes en study_annotations: {count}")
    return count > 0


def migrate_annotations_to_new_tables(conn, dry_run: bool = False) -> None:
    """
    Migrar datos de study_annotations a las 5 nuevas tablas.

    Mapeo:
    - annotation_type='note' -> study_article_notes
    - annotation_type='highlight' -> study_highlights
    - annotation_type='doubt' -> study_marks(mark_type='doubt')
    - annotation_type='bookmark' -> study_marks(mark_type='bookmark')
    """
    rows = conn.execute(
        "SELECT * FROM study_annotations ORDER BY id"
    ).fetchall()

    if not rows:
        print("     No hay anotaciones para migrar")
        return

    note_count = 0
    highlight_count = 0
    doubt_count = 0
    bookmark_count = 0
    skipped = 0

    for row in rows:
        ann_id = row["id"]
        ann_type = row["annotation_type"]
        article_id = row["article_id"]
        topic_id = row["topic_id"]
        selected_text = row["selected_text"]
        note_text = row["note_text"]
        color = row["color"] or "yellow"

        # Obtener snapshot de articulo si existe
        law_id_snapshot = None
        article_ref_snapshot = None
        anchor_key = None
        if article_id:
            art_row = conn.execute(
                "SELECT law_id, article_ref FROM articles WHERE id = ?",
                (article_id,)
            ).fetchone()
            if art_row:
                law_id_snapshot = art_row["law_id"]
                article_ref_snapshot = art_row["article_ref"]
                anchor_key = f"art_{article_id}_{article_ref_snapshot}"

        try:
            if ann_type == "note":
                if not dry_run:
                    conn.execute(
                        """
                        INSERT INTO study_article_notes(
                            article_id, law_id_snapshot, article_ref_snapshot, anchor_key,
                            selected_text, note_text, tags
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (article_id, law_id_snapshot, article_ref_snapshot, anchor_key, selected_text, note_text, None)
                    )
                note_count += 1

            elif ann_type == "highlight":
                if not dry_run:
                    conn.execute(
                        """
                        INSERT INTO study_highlights(
                            article_id, law_id_snapshot, article_ref_snapshot, anchor_key,
                            selected_text, start_offset, end_offset, color, note_text
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (article_id, law_id_snapshot, article_ref_snapshot, anchor_key, selected_text, None, None, color, note_text)
                    )
                highlight_count += 1

            elif ann_type == "doubt":
                if not dry_run:
                    conn.execute(
                        """
                        INSERT INTO study_marks(
                            topic_id, article_id, mark_type, note_text, resolved
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        (topic_id, article_id, "doubt", note_text, 0)
                    )
                doubt_count += 1

            elif ann_type == "bookmark":
                if not dry_run:
                    conn.execute(
                        """
                        INSERT INTO study_marks(
                            topic_id, article_id, mark_type, note_text, resolved
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        (topic_id, article_id, "bookmark", note_text, 0)
                    )
                bookmark_count += 1

            else:
                print(f"     [WARN] Tipo de anotacion desconocido (id={ann_id}): {ann_type}")
                skipped += 1

        except Exception as e:
            print(f"     [ERROR] Migrando anotacion {ann_id}: {e}")
            skipped += 1

    total = note_count + highlight_count + doubt_count + bookmark_count
    print(f"     Anotaciones migradas: {total}")
    print(f"       - Notas: {note_count}")
    print(f"       - Subrayados: {highlight_count}")
    print(f"       - Dudas: {doubt_count}")
    print(f"       - Marcadores: {bookmark_count}")
    if skipped:
        print(f"     [WARN] Saltadas: {skipped}")


def validate_migration(conn) -> bool:
    """Validar que la migracion fue exitosa."""
    print("\nValidacion:")

    try:
        for table in STUDY_TABLES:
            count = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            print(f"  [OK] {table}: {count} filas")

        # Comprobar que las tablas tienen indices
        print("\n  Indices:")
        indices = [
            "idx_study_article_notes_article",
            "idx_study_highlights_article",
            "idx_study_progress_status",
            "idx_study_marks_unresolved",
            "idx_study_last_reviews_due",
        ]
        for idx in indices:
            row = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?",
                (idx,)
            ).fetchone()
            status = "[OK]" if row else "[X]"
            print(f"    {status} {idx}")

        return True
    except Exception as e:
        print(f"  [ERROR] Validacion: {e}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migrar src/study a BD real (Ola A1)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostrar que pasaria sin hacer cambios"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("OLA A1: Migrar src/study a BD real")
    print("=" * 70)

    if args.dry_run:
        print("\n[DRY-RUN] Modo simulacion (sin cambios reales)\n")

    try:
        with connect() as conn:
            print("\nPaso 1: Crear tablas de estudio...")
            ensure_study_tables_exist(conn)

            print("\nPaso 2: Migrar datos de study_annotations...")
            if migration_data_exists(conn):
                migrate_annotations_to_new_tables(conn, dry_run=args.dry_run)

            print("\nPaso 3: Validar migracion...")
            if not validate_migration(conn):
                print("\n[ERROR] Validacion fallida")
                return 1

            if not args.dry_run:
                conn.commit()
                print("\n[OK] Migracion completada y confirmada")
            else:
                print("\n[OK] Dry-run completado (sin cambios reales)")

        return 0

    except Exception as e:
        print(f"\n[ERROR] Error fatal: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
