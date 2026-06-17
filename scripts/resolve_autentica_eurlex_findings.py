#!/usr/bin/env python3
"""
Resolver los 6 hallazgos 'autentica_fuente_oficial_no_importada' cuya norma
EUR-Lex ya ha sido importada (Carta UE, RGPD, Reglamento 2024/2509).

Acciones por tema:
  1. Crear enlace topic_sources (tema -> norma) si no existe.
     mapping_basis = 'autentica_auxiliar_pendiente_validacion'
     (la fuente esta importada, pero el articulado exacto sigue pendiente
      de validacion juridica humana)
  2. Marcar el hallazgo 'autentica_fuente_oficial_no_importada' como resuelto.

NO toca el articulado: la delimitacion de articulos concretos (p.ej. Carta art. 41)
permanece como tarea de validacion fina separada.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.db import connect

# topic_number (especial) -> (law_id, normative_reference)
TOPIC_LAW_MAP = {
    26: (82, "Carta de Derechos Fundamentales de la Union Europea"),
    29: (83, "Reglamento UE 2016/679 Proteccion Datos RGPD"),
    30: (84, "Reglamento UE/Euratom 2024/2509 Normas financieras presupuesto UE"),
    48: (82, "Carta de Derechos Fundamentales de la Union Europea"),
    49: (82, "Carta de Derechos Fundamentales de la Union Europea"),
    50: (82, "Carta de Derechos Fundamentales de la Union Europea"),
}

MAPPING_BASIS = "autentica_auxiliar_pendiente_validacion"


def resolve():
    summary = {"links_created": 0, "links_existing": 0, "findings_resolved": 0, "errors": 0}

    with connect() as conn:
        for tnum, (law_id, ref) in TOPIC_LAW_MAP.items():
            trow = conn.execute(
                "SELECT id FROM topics WHERE topic_number=? AND part='especial'",
                (tnum,),
            ).fetchone()
            if not trow:
                print(f"  ERROR: topic_number {tnum} (especial) no encontrado")
                summary["errors"] += 1
                continue
            topic_id = trow[0]

            # 1. Crear enlace topic_sources si no existe
            existing = conn.execute(
                "SELECT id FROM topic_sources WHERE topic_id=? AND law_id=?",
                (topic_id, law_id),
            ).fetchone()

            if existing:
                summary["links_existing"] += 1
                print(f"  Topic {tnum}: enlace ya existe (law {law_id})")
            else:
                conn.execute(
                    """
                    INSERT INTO topic_sources(
                        topic_id, law_id, article_id, normative_reference,
                        coverage_status, mapping_basis, priority,
                        validation_status, notes
                    ) VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        topic_id,
                        law_id,
                        ref,
                        "cubierto_fuente_importada",
                        MAPPING_BASIS,
                        "alta",
                        "pendiente_de_validacion",
                        "Fuente EUR-Lex importada; articulado exacto pendiente de validacion juridica humana.",
                    ),
                )
                summary["links_created"] += 1
                print(f"  Topic {tnum}: enlace CREADO -> {ref} (law {law_id})")

            # 2. Marcar hallazgo como resuelto
            updated = conn.execute(
                """
                UPDATE topic_validation_findings
                SET status='resuelto', updated_at=CURRENT_TIMESTAMP
                WHERE topic_id=?
                  AND finding_type='autentica_fuente_oficial_no_importada'
                  AND status='abierto'
                """,
                (topic_id,),
            ).rowcount
            summary["findings_resolved"] += updated
            if updated:
                print(f"    -> hallazgo 'fuente no importada' resuelto")

        conn.commit()

    return summary


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("RESOLVIENDO HALLAZGOS autentica_fuente_oficial_no_importada")
    print("=" * 70 + "\n")
    result = resolve()
    print("\n" + "=" * 70)
    print(f"RESULTADO: {result}")
    print("=" * 70 + "\n")
