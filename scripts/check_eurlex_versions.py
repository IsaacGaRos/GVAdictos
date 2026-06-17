from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_source_updates import sha256_bytes
from src.core.db import connect, init_db
from src.laws.importer import import_law
from scripts.import_official_sources import convert_to_text


ROOT = Path(__file__).resolve().parents[1]
SPARQL_ENDPOINT = "https://publications.europa.eu/webapi/rdf/sparql"
PROCESSED_DIR = ROOT / "data" / "processed" / "official_sources"


@dataclass(frozen=True)
class EurlexTarget:
    label: str
    celex_prefix: str
    external_prefix: str
    title_prefix: str
    local_path: Path


TARGETS = [
    EurlexTarget(
        label="TUE",
        celex_prefix="02016M/TXT",
        external_prefix="EURLEX-02016M-TXT",
        title_prefix="Tratado de la Union Europea version consolidada",
        local_path=ROOT
        / "data"
        / "sources"
        / "leyes_originales"
        / "EURLEX"
        / "EURLEX-02016M-TXT-20250315_TUE_consolidado_2025-03-15.html",
    ),
    EurlexTarget(
        label="TFUE",
        celex_prefix="02016E/TXT",
        external_prefix="EURLEX-02016E-TXT",
        title_prefix="Tratado de Funcionamiento de la Union Europea version consolidada",
        local_path=ROOT
        / "data"
        / "sources"
        / "leyes_originales"
        / "EURLEX"
        / "EURLEX-02016E-TXT-20250315_TFUE_consolidado_2025-03-15.html",
    ),
    EurlexTarget(
        label="Carta UE",
        celex_prefix="12016P/TXT",
        external_prefix="EURLEX-12016P-TXT",
        title_prefix="Carta de Derechos Fundamentales de la Union Europea",
        local_path=ROOT
        / "data"
        / "sources"
        / "leyes_originales"
        / "EURLEX"
        / "EURLEX-12016P-TXT_Carta_Derechos_Fundamentales_UE.html",
    ),
    EurlexTarget(
        label="RGPD",
        celex_prefix="32016R0679",
        external_prefix="EURLEX-32016R0679",
        title_prefix="Reglamento UE 2016/679 Proteccion Datos RGPD",
        local_path=ROOT
        / "data"
        / "sources"
        / "leyes_originales"
        / "EURLEX"
        / "EURLEX-32016R0679_RGPD.html",
    ),
    EurlexTarget(
        label="Reglamento UE/Euratom 2024/2509",
        celex_prefix="32024R2509",
        external_prefix="EURLEX-32024R2509",
        title_prefix="Reglamento UE/Euratom 2024/2509 Normas financieras presupuesto UE",
        local_path=ROOT
        / "data"
        / "sources"
        / "leyes_originales"
        / "EURLEX"
        / "EURLEX-32024R2509_Reglamento_Financiero_UE_2024.html",
    ),
]


def sparql_latest_version(celex_prefix: str) -> tuple[str, str]:
    query = f"""
    PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
    SELECT ?celex ?date WHERE {{
      ?work cdm:resource_legal_id_celex ?celex .
      FILTER(STRSTARTS(STR(?celex), "{celex_prefix}-"))
      OPTIONAL {{ ?work cdm:work_date_document ?date }}
    }}
    ORDER BY DESC(?date)
    LIMIT 1
    """
    data = urllib.parse.urlencode({"query": query, "format": "application/sparql-results+json"}).encode()
    request = urllib.request.Request(
        SPARQL_ENDPOINT,
        data=data,
        headers={
            "Accept": "application/sparql-results+json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "GVAdicto/0.1",
        },
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = json.loads(response.read().decode("utf-8"))
    bindings = payload.get("results", {}).get("bindings", [])
    if not bindings:
        raise RuntimeError(f"No EUR-Lex version found for {celex_prefix}")
    row = bindings[0]
    return row["celex"]["value"], row["date"]["value"]


def celex_xhtml_url(celex: str) -> str:
    return f"http://publications.europa.eu/resource/celex/{celex.replace('/', '%2F')}.SPA.xhtml"


def fetch_url(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/xhtml+xml,text/html",
            "User-Agent": "GVAdicto/0.1",
        },
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def local_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    return sha256_bytes(path.read_bytes())


def source_row(conn, target: EurlexTarget):
    return conn.execute(
        """
        SELECT *
        FROM source_documents
        WHERE source_kind = 'eurlex_html'
          AND external_id LIKE ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (f"{target.external_prefix}%",),
    ).fetchone()


def update_source_row(conn, row_id: int, target: EurlexTarget, celex: str, date: str, url: str) -> None:
    external_id = f"EURLEX-{celex.replace('/', '-').replace('_', '-')}"
    title = f"{target.title_prefix} {date}"
    notes = (
        "XHTML oficial Publications Office/EUR-Lex; version consolidada detectada por SPARQL; "
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
            str(target.local_path.relative_to(ROOT)).replace("\\", "/"),
            "text/html",
            url,
            notes,
            row_id,
        ),
    )


def import_updated_source(target: EurlexTarget, celex: str, date: str) -> int:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    text_path = PROCESSED_DIR / f"EURLEX-{celex.replace('/', '-')}.txt"
    text_path.write_text(convert_to_text(target.local_path, "text/html"), encoding="utf-8")
    return import_law(text_path, f"{target.title_prefix} {date}", original_source_path=target.local_path)


def check_eurlex(update_files: bool = False, import_updated: bool = False) -> dict[str, int]:
    init_db()
    summary = {"checked": 0, "changed": 0, "updated_files": 0, "imported": 0, "errors": 0}
    pending_imports: list[tuple[EurlexTarget, str, str]] = []
    with connect() as conn:
        for target in TARGETS:
            summary["checked"] += 1
            row = source_row(conn, target)
            if row is None:
                summary["errors"] += 1
                print(f"ERROR {target.label}: source_documents row not found")
                continue
            try:
                latest_celex, latest_date = sparql_latest_version(target.celex_prefix)
                url = celex_xhtml_url(latest_celex)
                data = fetch_url(url)
                remote_hash = sha256_bytes(data)
                previous_hash = local_hash(target.local_path)
                changed = int(previous_hash != remote_hash or row["url"] != url)
                if changed:
                    summary["changed"] += 1
                    if update_files:
                        target.local_path.parent.mkdir(parents=True, exist_ok=True)
                        target.local_path.write_bytes(data)
                        update_source_row(conn, row["id"], target, latest_celex, latest_date, url)
                        summary["updated_files"] += 1
                        if import_updated:
                            pending_imports.append((target, latest_celex, latest_date))
                conn.execute(
                    """
                    INSERT INTO source_update_checks(
                        source_document_id, url, status, content_hash,
                        previous_hash, changed, local_path, error
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["id"],
                        url,
                        "ok",
                        remote_hash,
                        previous_hash,
                        changed,
                        str(target.local_path.relative_to(ROOT)).replace("\\", "/"),
                        None,
                    ),
                )
                print(f"{target.label}: latest={latest_celex} date={latest_date} changed={changed}")
            except Exception as exc:
                summary["errors"] += 1
                conn.execute(
                    """
                    INSERT INTO source_update_checks(
                        source_document_id, url, status, content_hash,
                        previous_hash, changed, local_path, error
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["id"],
                        row["url"],
                        "error",
                        None,
                        local_hash(target.local_path),
                        0,
                        str(target.local_path.relative_to(ROOT)).replace("\\", "/"),
                        str(exc),
                    ),
                )
                print(f"ERROR {target.label}: {exc}")
    for target, latest_celex, latest_date in pending_imports:
        import_updated_source(target, latest_celex, latest_date)
        summary["imported"] += 1
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Comprueba versiones consolidadas EUR-Lex TUE/TFUE.")
    parser.add_argument("--update-files", action="store_true", help="Descarga la ultima version si cambia.")
    parser.add_argument("--import-updated", action="store_true", help="Reimporta en SQLite si se actualiza.")
    args = parser.parse_args()
    print(check_eurlex(update_files=args.update_files, import_updated=args.import_updated))


if __name__ == "__main__":
    main()
