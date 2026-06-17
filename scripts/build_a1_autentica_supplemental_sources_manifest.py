from __future__ import annotations

import csv
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data" / "sources" / "official_normative_sources_a1_autentica_supplemental.csv"


@dataclass(frozen=True)
class Source:
    source_kind: str
    external_id: str
    title: str
    path: str
    mime_type: str
    url: str
    priority: str = "alta"
    legal_status: str = "pendiente_de_validacion"
    notes: str = ""


def boe_pdf_url(year: int, external_id: str) -> str:
    return f"https://www.boe.es/buscar/pdf/{year}/{external_id}-consolidado.pdf"


SOURCES: list[Source] = [
    Source(
        "boe_consolidado",
        "BOE-A-1987-12077",
        "Ley Organica 2/1987 Conflictos Jurisdiccionales",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-1987-12077_LO_2-1987_Conflictos_Jurisdiccionales.pdf",
        "application/pdf",
        boe_pdf_url(1987, "BOE-A-1987-12077"),
        notes="Indicacion auxiliar Autentica para tema PE-03.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-2003-20254",
        "Ley 33/2003 Patrimonio Administraciones Publicas",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-2003-20254_Ley_33-2003_Patrimonio_AAPP.pdf",
        "application/pdf",
        boe_pdf_url(2003, "BOE-A-2003-20254"),
        notes="Indicacion auxiliar Autentica para legislacion basica estatal de patrimonio.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-1986-1216",
        "Real Decreto 33/1986 Regimen Disciplinario Funcionarios",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-1986-1216_RD_33-1986_Regimen_Disciplinario.pdf",
        "application/pdf",
        boe_pdf_url(1986, "BOE-A-1986-1216"),
        notes="Indicacion auxiliar Autentica para regimen disciplinario.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-1998-8202",
        "Ley 13/1997 Tramo autonomico IRPF y tributos cedidos CV",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-1998-8202_Ley_13-1997_Tributos_Cedidos_CV.pdf",
        "application/pdf",
        boe_pdf_url(1998, "BOE-A-1998-8202"),
        notes="Indicacion auxiliar Autentica para financiacion autonomica.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-2001-24963",
        "Ley 22/2001 Fondos de Compensacion Interterritorial",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-2001-24963_Ley_22-2001_Fondos_Compensacion_Interterritorial.pdf",
        "application/pdf",
        boe_pdf_url(2001, "BOE-A-2001-24963"),
        notes="Indicacion auxiliar Autentica para financiacion autonomica.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-2014-8132",
        "Real Decreto 635/2014 Periodo Medio Pago Proveedores",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-2014-8132_RD_635-2014_PMP.pdf",
        "application/pdf",
        boe_pdf_url(2014, "BOE-A-2014-8132"),
        notes="Indicacion auxiliar Autentica para periodo medio de pago a proveedores.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-2019-967",
        "Ley 25/2018 Grupos de Interes Comunitat Valenciana",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-2019-967_Ley_25-2018_Grupos_Interes_CV.pdf",
        "application/pdf",
        boe_pdf_url(2019, "BOE-A-2019-967"),
        notes="Indicacion auxiliar Autentica para gobierno abierto y grupos de interes.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-2016-11021",
        "Ley 8/2016 Incompatibilidades Conflictos Intereses Cargos Publicos CV",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-2016-11021_Ley_8-2016_Conflictos_Intereses_CV.pdf",
        "application/pdf",
        boe_pdf_url(2016, "BOE-A-2016-11021"),
        notes="Indicacion auxiliar Autentica para conflicto de interes autonomico.",
    ),
    Source(
        "dogv_pdf",
        "DOGV-A-20061218-R-20240306-CORTS",
        "Reglamento de Les Corts consolidado DOGV",
        "data/sources/leyes_originales/DOGV/DOGV-A_20061218_R_20240306_Reglamento_Les_Corts.pdf",
        "application/pdf",
        "https://dogv.gva.es/auto/docvpub/rlgv/2006/A_20061218_ca_R_20240306.pdf",
        notes="Indicacion auxiliar Autentica para tema PG-08.",
    ),
    Source(
        "dogv_html",
        "DOGV-2017-860",
        "Decreto 3/2017 Seleccion Provision Movilidad Funcion Publica Valenciana",
        "data/sources/leyes_originales/DOGV/DOGV-2017-860_Decreto_3-2017_Seleccion_Provision_Movilidad.html",
        "text/html",
        "https://dogv.gva.es/es/resultat-dogv?L=0&sig=000860%2F2017&url_lista=",
        notes="Indicacion auxiliar Autentica para temas PE-35 y PE-36.",
    ),
    Source(
        "dogv_pdf",
        "DOGV-D-2019-042-CONS",
        "Decreto 42/2019 Condiciones Trabajo Personal Funcionario Generalitat consolidado DOGV",
        "data/sources/leyes_originales/DOGV/DOGV-D_2019_042_Decreto_42-2019_Condiciones_Trabajo.pdf",
        "application/pdf",
        "https://dogv.gva.es/auto/docvpub/rlgv/2019/D_2019_042_ca_TS_20220629.pdf",
        notes="Indicacion auxiliar Autentica para permisos y condiciones de trabajo; pendiente comprobar modificaciones posteriores.",
    ),
    Source(
        "dogv_html",
        "DOGV-D-2021-049",
        "Decreto 49/2021 Teletrabajo Generalitat",
        "data/sources/leyes_originales/DOGV/DOGV-D_2021_049_Decreto_49-2021_Teletrabajo.html",
        "text/html",
        "https://dogv.gva.es/es/eli/es-vc/d/2021/04/01/49/",
        notes="Indicacion auxiliar Autentica para teletrabajo.",
    ),
    Source(
        "dogv_html",
        "DOGV-2017-2595",
        "Decreto 25/2017 Fondos de Caja Fija",
        "data/sources/leyes_originales/DOGV/DOGV-2017-2595_Decreto_25-2017_Caja_Fija.html",
        "text/html",
        "https://dogv.gva.es/portal/ficha_disposicion.jsp?L=1&sig=002595%2F2017&url_lista=+",
        notes="Indicacion auxiliar Autentica para gestion presupuestaria.",
    ),
    Source(
        "dogv_pdf",
        "DOGV-2024-4",
        "Orden 18/2023 NEFIS",
        "data/sources/leyes_originales/DOGV/DOGV-2024-4_Orden_18-2023_NEFIS.pdf",
        "application/pdf",
        "https://dogv.gva.es/datos/2024/01/04/pdf/2024_4.pdf",
        notes="Indicacion auxiliar Autentica para normas de funcionamiento del presupuesto.",
    ),
    Source(
        "dogv_html",
        "DOGV-2001-5331",
        "Orden 27 diciembre 2001 Clasificacion Economica Generalitat",
        "data/sources/leyes_originales/DOGV/DOGV-2001-5331_Orden_Clasificacion_Economica.html",
        "text/html",
        "https://dogv.gva.es/es/disposicio?sig=5331/2001&url_lista=",
        notes="Indicacion auxiliar Autentica para clasificacion economica presupuestaria.",
    ),
    Source(
        "eurlex_html",
        "EURLEX-12012P-TXT",
        "Carta de Derechos Fundamentales de la Union Europea",
        "data/sources/leyes_originales/EURLEX/EURLEX-12012P-TXT_Carta_Derechos_Fundamentales_UE.html",
        "text/html",
        "https://eur-lex.europa.eu/legal-content/ES/TXT/HTML/?uri=CELEX:12012P/TXT",
        notes="Indicacion auxiliar Autentica para temas UE y buena administracion.",
    ),
    Source(
        "eurlex_html",
        "EURLEX-02016R0679-20160504",
        "Reglamento UE 2016/679 Proteccion Datos RGPD",
        "data/sources/leyes_originales/EURLEX/EURLEX-02016R0679-20160504_RGPD.html",
        "text/html",
        "https://eur-lex.europa.eu/legal-content/ES/TXT/HTML/?uri=CELEX:02016R0679-20160504",
        notes="Indicacion auxiliar Autentica para proteccion de datos.",
    ),
    Source(
        "eurlex_html",
        "EURLEX-32024R2509",
        "Reglamento UE Euratom 2024/2509 Normas financieras presupuesto UE",
        "data/sources/leyes_originales/EURLEX/EURLEX-32024R2509_Reglamento_Financiero_UE_2024.html",
        "text/html",
        "https://eur-lex.europa.eu/legal-content/ES/TXT/HTML/?uri=CELEX:32024R2509",
        notes="Sustituye al Reglamento UE Euratom 2018/1046 citado por Autentica para conflicto de interes en fondos europeos; requiere validacion fina.",
    ),
]


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "GVAdicto/0.1"})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def content_ok(data: bytes, mime_type: str) -> bool:
    if mime_type == "application/pdf":
        return data.startswith(b"%PDF")
    return bool(data.strip())


def main() -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for source in SOURCES:
        local_path = ROOT / source.path
        local_path.parent.mkdir(parents=True, exist_ok=True)
        status = "descargado"
        try:
            data = fetch(source.url)
            if not content_ok(data, source.mime_type):
                status = "error_descarga"
            else:
                local_path.write_bytes(data)
        except Exception as exc:
            status = "error_descarga"
            print(f"ERROR {source.external_id}: {exc}")

        rows.append(
            {
                "source_kind": source.source_kind,
                "external_id": source.external_id,
                "title": source.title,
                "path": source.path,
                "mime_type": source.mime_type,
                "url": source.url,
                "created_time": "",
                "modified_time": "",
                "priority": source.priority,
                "status": status,
                "legal_status": source.legal_status,
                "notes": source.notes,
            }
        )
        print(f"{status}: {source.external_id} - {source.title}")

    with MANIFEST_PATH.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "source_kind",
                "external_id",
                "title",
                "path",
                "mime_type",
                "url",
                "created_time",
                "modified_time",
                "priority",
                "status",
                "legal_status",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Manifest written: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
