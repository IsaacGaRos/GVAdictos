#!/usr/bin/env python3
"""
Importar EUR-Lex directamente desde URLs verificadas (sin SPARQL).
Para Carta UE, RGPD y Reglamento 2024/2509.
"""
import sys
import urllib.request
import urllib.error
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_source_updates import sha256_bytes
from src.core.db import connect, init_db
from src.laws.importer import import_law
from scripts.import_official_sources import convert_to_text

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed" / "official_sources"
EURLEX_DIR = ROOT / "data" / "sources" / "leyes_originales" / "EURLEX"


@dataclass(frozen=True)
class DirectEurlexTarget:
    label: str
    url: str
    celex: str
    external_id: str
    title: str
    local_filename: str
    topic_ids: list[int]


TARGETS = [
    DirectEurlexTarget(
        label="Carta de Derechos Fundamentales UE",
        url="https://eur-lex.europa.eu/legal-content/ES/TXT/XHTML/?uri=CELEX:12016P/TXT",
        celex="12016P/TXT",
        external_id="EURLEX-12016P-TXT",
        title="Carta de Derechos Fundamentales de la Union Europea",
        local_filename="EURLEX-12016P-TXT_Carta_Derechos_Fundamentales_UE.html",
        topic_ids=[41, 48, 49, 50],
    ),
    DirectEurlexTarget(
        label="RGPD",
        url="https://eur-lex.europa.eu/legal-content/ES/TXT/XHTML/?uri=CELEX:02016R0679-20160504",
        celex="32016R0679",
        external_id="EURLEX-32016R0679",
        title="Reglamento UE 2016/679 Proteccion Datos RGPD",
        local_filename="EURLEX-32016R0679_RGPD.html",
        topic_ids=[44],
    ),
    DirectEurlexTarget(
        label="Reglamento UE/Euratom 2024/2509",
        url="https://eur-lex.europa.eu/legal-content/ES/TXT/XHTML/?uri=CELEX:32024R2509",
        celex="32024R2509",
        external_id="EURLEX-32024R2509",
        title="Reglamento UE/Euratom 2024/2509 Normas financieras presupuesto UE",
        local_filename="EURLEX-32024R2509_Reglamento_Financiero_UE_2024.html",
        topic_ids=[45],
    ),
]


def fetch_url(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/xhtml+xml,text/html",
            "User-Agent": "GVAdicto/0.1",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return response.read()
    except urllib.error.URLError as e:
        raise RuntimeError(f"URL error for {url}: {e}")
    except Exception as e:
        raise RuntimeError(f"Error fetching {url}: {e}")


def update_source_row(conn, source_id: int, target: DirectEurlexTarget, data: bytes) -> None:
    remote_hash = sha256_bytes(data)
    url = target.url
    title = target.title
    external_id = target.external_id
    notes = (
        "XHTML oficial Publications Office/EUR-Lex descargado directamente; "
        "version verificada por usuario; "
        "instrumento documental sin efecto juridico propio segun EUR-Lex."
    )

    conn.execute(
        """
        UPDATE source_documents
        SET external_id = ?, title = ?, path = ?, mime_type = ?, url = ?,
            priority = 'alta', status = 'descargado',
            legal_status = 'pendiente_de_validacion', notes = ?
        WHERE id = ?
        """,
        (
            external_id,
            title,
            str((EURLEX_DIR / target.local_filename).relative_to(ROOT)).replace("\\", "/"),
            "text/html",
            url,
            notes,
            source_id,
        ),
    )


def import_law_wrapper(local_path: Path, title: str) -> int:
    return import_law(local_path, title, original_source_path=local_path)


def import_eurlex_direct() -> dict:
    init_db()
    EURLEX_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    summary = {"checked": 0, "downloaded": 0, "imported": 0, "errors": 0}
    pending_imports = []  # Collect imports to do after closing connection

    # Phase 1: Download and update source_documents
    with connect() as conn:
        for target in TARGETS:
            summary["checked"] += 1
            print(f"\n[{target.label}]")

            # Buscar source_documents fila
            row = conn.execute(
                """
                SELECT id FROM source_documents
                WHERE external_id = ? OR external_id LIKE ?
                LIMIT 1
                """,
                (target.external_id, f"{target.external_id}%"),
            ).fetchone()

            if not row:
                summary["errors"] += 1
                print(f"  ERROR: No source_documents row found for {target.external_id}")
                continue

            source_id = row[0]
            local_path = EURLEX_DIR / target.local_filename

            try:
                print(f"  Descargando desde: {target.url}")
                data = fetch_url(target.url)
                remote_hash = sha256_bytes(data)
                print(f"  SHA-256: {remote_hash[:16]}...")

                # Guardar fichero local
                local_path.write_bytes(data)
                print(f"  [OK] Guardado: {local_path.name} ({len(data)/1024:.1f} KB)")
                summary["downloaded"] += 1

                # Actualizar source_documents
                update_source_row(conn, source_id, target, data)

                # Preparar para importacion (después de cerrar conexión)
                text_path = PROCESSED_DIR / f"{target.celex.replace('/', '-')}.txt"
                pending_imports.append((local_path, text_path, target))

            except Exception as exc:
                summary["errors"] += 1
                print(f"  ERROR: {exc}")

        conn.commit()

    # Phase 2: Import texts (connection closed, no locking issues)
    for local_path, text_path, target in pending_imports:
        try:
            print(f"  Convirtiendo a texto...")
            text = convert_to_text(local_path, "text/html")
            text_path.write_text(text, encoding="utf-8")

            print(f"  Importando a SQLite...")
            law_id = import_law_wrapper(text_path, target.title)
            print(f"  [OK] Importado como law_id {law_id}")
            summary["imported"] += 1

        except Exception as exc:
            summary["errors"] += 1
            print(f"  ERROR import: {exc}")

    # Phase 3: Mark findings as resolved
    with connect() as conn:
        for _, _, target in pending_imports:
            for topic_id in target.topic_ids:
                finding_rows = conn.execute(
                    """
                    SELECT id FROM topic_validation_findings
                    WHERE topic_id = ?
                      AND finding_type IN ('fuente_eurlex_pendiente', 'fuente_europea_pendiente')
                      AND status = 'abierto'
                    """,
                    (topic_id,),
                ).fetchall()

                for finding_row in finding_rows:
                    conn.execute(
                        """
                        UPDATE topic_validation_findings
                        SET status = 'resuelto'
                        WHERE id = ?
                        """,
                        (finding_row[0],),
                    )

            print(f"  [OK] Hallazgos de validacion resueltos para topics: {target.topic_ids}")

        conn.commit()

    return summary


def main():
    import io
    import sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    print("\n" + "="*80)
    print("IMPORTACION EUR-LEX DIRECTA (SIN SPARQL)")
    print("="*80)
    result = import_eurlex_direct()
    print("\n" + "="*80)
    print(f"RESULTADO: {result}")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
