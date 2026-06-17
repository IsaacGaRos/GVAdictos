from __future__ import annotations

import csv
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data" / "sources" / "official_normative_sources_a1_topic_validation.csv"


@dataclass(frozen=True)
class Source:
    source_kind: str
    external_id: str
    title: str
    path: str
    url: str
    priority: str = "alta"
    legal_status: str = "pendiente_de_validacion"
    notes: str = ""


def boe_pdf_url(year: int, external_id: str) -> str:
    return f"https://www.boe.es/buscar/pdf/{year}/{external_id}-consolidado.pdf"


SOURCES: list[Source] = [
    Source(
        "boe_consolidado",
        "BOE-A-1997-25336",
        "Ley 50/1997 Gobierno",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-1997-25336_Ley_50-1997_Gobierno.pdf",
        boe_pdf_url(1997, "BOE-A-1997-25336"),
        notes="Fuente implicita para temas de Gobierno y Consejo de Ministros.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-1985-12666",
        "Ley Organica 6/1985 Poder Judicial",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-1985-12666_LO_6-1985_Poder_Judicial.pdf",
        boe_pdf_url(1985, "BOE-A-1985-12666"),
        notes="Fuente implicita para Poder Judicial y CGPJ.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-1979-23709",
        "Ley Organica 2/1979 Tribunal Constitucional",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-1979-23709_LO_2-1979_Tribunal_Constitucional.pdf",
        boe_pdf_url(1979, "BOE-A-1979-23709"),
        notes="Fuente implicita para Tribunal Constitucional y procesos constitucionales.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-1981-10325",
        "Ley Organica 3/1981 Defensor del Pueblo",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-1981-10325_LO_3-1981_Defensor_Pueblo.pdf",
        boe_pdf_url(1981, "BOE-A-1981-10325"),
        notes="Fuente implicita para Defensor del Pueblo.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-1982-11584",
        "Ley Organica 2/1982 Tribunal de Cuentas",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-1982-11584_LO_2-1982_Tribunal_Cuentas.pdf",
        boe_pdf_url(1982, "BOE-A-1982-11584"),
        notes="Fuente implicita para Tribunal de Cuentas y responsabilidad contable.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-1988-8678",
        "Ley 7/1988 Funcionamiento Tribunal de Cuentas",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-1988-8678_Ley_7-1988_Funcionamiento_Tribunal_Cuentas.pdf",
        boe_pdf_url(1988, "BOE-A-1988-8678"),
        notes="Fuente complementaria para enjuiciamiento contable y funcionamiento del Tribunal de Cuentas.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-1982-17235",
        "Ley Organica 5/1982 Estatuto Autonomia Comunitat Valenciana",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-1982-17235_LO_5-1982_Estatuto_Autonomia_CV.pdf",
        boe_pdf_url(1982, "BOE-A-1982-17235"),
        notes="Fuente nuclear para organizacion y competencias de la Generalitat.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-1985-11672",
        "Ley Organica 5/1985 Regimen Electoral General",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-1985-11672_LOREG.pdf",
        boe_pdf_url(1985, "BOE-A-1985-11672"),
        notes="Fuente basica para derecho de sufragio y regimen electoral.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-1987-9636",
        "Ley 1/1987 Electoral Valenciana",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-1987-9636_Ley_1-1987_Electoral_Valenciana.pdf",
        boe_pdf_url(1987, "BOE-A-1987-9636"),
        notes="Fuente especifica para sistema electoral valenciano.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-2021-6051",
        "Ley 2/2021 Sindic de Greuges Comunitat Valenciana",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-2021-6051_Ley_2-2021_Sindic_Greuges.pdf",
        boe_pdf_url(2021, "BOE-A-2021-6051"),
        notes="Fuente vigente para el Sindic de Greuges; sustituye la Ley 11/1988.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-1985-18239",
        "Ley 6/1985 Sindicatura de Cuentas",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-1985-18239_Ley_6-1985_Sindicatura_Cuentas.pdf",
        boe_pdf_url(1985, "BOE-A-1985-18239"),
        notes="Fuente especifica para Sindicatura de Comptes.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-1995-1949",
        "Ley 10/1994 Consell Juridic Consultiu Comunitat Valenciana",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-1995-1949_Ley_10-1994_Consell_Juridic_Consultiu.pdf",
        boe_pdf_url(1995, "BOE-A-1995-1949"),
        notes="Fuente especifica para el Consell Juridic Consultiu.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-1986-2791",
        "Ley 12/1985 Consell Valencia de Cultura",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-1986-2791_Ley_12-1985_Consell_Valencia_Cultura.pdf",
        boe_pdf_url(1986, "BOE-A-1986-2791"),
        notes="Fuente especifica para el Consell Valencia de Cultura.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-1998-24262",
        "Ley 7/1998 Academia Valenciana de la Llengua",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-1998-24262_Ley_7-1998_AVL.pdf",
        boe_pdf_url(1998, "BOE-A-1998-24262"),
        notes="Fuente especifica para la Academia Valenciana de la Llengua.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-2014-2949",
        "Ley 1/2014 Comite Economic i Social Comunitat Valenciana",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-2014-2949_Ley_1-2014_CES_CV.pdf",
        boe_pdf_url(2014, "BOE-A-2014-2949"),
        notes="Fuente especifica para el Comite Economic i Social.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-1998-16718",
        "Ley 29/1998 Jurisdiccion Contencioso Administrativa",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-1998-16718_Ley_29-1998_LJCA.pdf",
        boe_pdf_url(1998, "BOE-A-1998-16718"),
        notes="Fuente nuclear para jurisdiccion contencioso-administrativa.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-1954-15431",
        "Ley de Expropiacion Forzosa 1954",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-1954-15431_Ley_Expropiacion_Forzosa.pdf",
        boe_pdf_url(1954, "BOE-A-1954-15431"),
        notes="Fuente nuclear para expropiacion forzosa.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-1957-7998",
        "Reglamento Ley Expropiacion Forzosa 1957",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-1957-7998_Reglamento_Expropiacion_Forzosa.pdf",
        boe_pdf_url(1957, "BOE-A-1957-7998"),
        notes="Fuente reglamentaria complementaria para expropiacion forzosa.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-2015-11724",
        "Real Decreto Legislativo 8/2015 Ley General Seguridad Social",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-2015-11724_RDL_8-2015_LGSS.pdf",
        boe_pdf_url(2015, "BOE-A-2015-11724"),
        notes="Fuente nuclear para sistema de Seguridad Social.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-2003-21614",
        "Ley 47/2003 General Presupuestaria",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-2003-21614_Ley_47-2003_General_Presupuestaria.pdf",
        boe_pdf_url(2003, "BOE-A-2003-21614"),
        notes="Fuente estatal complementaria para regimen presupuestario.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-2013-12887",
        "Ley 19/2013 Transparencia Acceso Informacion Buen Gobierno",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-2013-12887_Ley_19-2013_Transparencia.pdf",
        boe_pdf_url(2013, "BOE-A-2013-12887"),
        notes="Fuente basica estatal para transparencia y buen gobierno.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-2022-8187",
        "Ley 1/2022 Transparencia Buen Gobierno Comunitat Valenciana",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-2022-8187_Ley_1-2022_Transparencia_CV.pdf",
        boe_pdf_url(2022, "BOE-A-2022-8187"),
        notes="Fuente autonomica para transparencia y buen gobierno.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-2023-10640",
        "Ley 4/2023 Participacion Ciudadana Comunitat Valenciana",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-2023-10640_Ley_4-2023_Participacion_Ciudadana_CV.pdf",
        boe_pdf_url(2023, "BOE-A-2023-10640"),
        notes="Fuente autonomica para participacion ciudadana.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-2018-16673",
        "Ley Organica 3/2018 Proteccion Datos Derechos Digitales",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-2018-16673_LO_3-2018_Proteccion_Datos.pdf",
        boe_pdf_url(2018, "BOE-A-2018-16673"),
        notes="Fuente estatal para proteccion de datos y derechos digitales.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-2023-4513",
        "Ley 2/2023 Proteccion Informantes",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-2023-4513_Ley_2-2023_Proteccion_Informantes.pdf",
        boe_pdf_url(2023, "BOE-A-2023-4513"),
        notes="Fuente estatal para proteccion de informantes.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-1985-151",
        "Ley 53/1984 Incompatibilidades Personal Administraciones Publicas",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-1985-151_Ley_53-1984_Incompatibilidades.pdf",
        boe_pdf_url(1985, "BOE-A-1985-151"),
        notes="Fuente basica para incompatibilidades del personal empleado publico.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-1995-24292",
        "Ley 31/1995 Prevencion Riesgos Laborales",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-1995-24292_Ley_31-1995_PRL.pdf",
        boe_pdf_url(1995, "BOE-A-1995-24292"),
        notes="Fuente basica para seguridad y salud laboral en empleo publico.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-1980-21166",
        "Ley Organica 8/1980 Financiacion Comunidades Autonomas",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-1980-21166_LOFCA.pdf",
        boe_pdf_url(1980, "BOE-A-1980-21166"),
        notes="Fuente nuclear para financiacion de comunidades autonomas.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-2009-20375",
        "Ley 22/2009 Sistema Financiacion Comunidades Autonomas",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-2009-20375_Ley_22-2009_Sistema_Financiacion_CCAA.pdf",
        boe_pdf_url(2009, "BOE-A-2009-20375"),
        notes="Fuente estatal para sistema de financiacion de comunidades autonomas de regimen comun.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-2019-3489",
        "Ley 3/2019 Servicios Sociales Inclusivos Comunitat Valenciana",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-2019-3489_Ley_3-2019_Servicios_Sociales_CV.pdf",
        boe_pdf_url(2019, "BOE-A-2019-3489"),
        notes="Fuente sectorial candidata para competencias de servicios sociales.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-2019-1986",
        "Ley 26/2018 Derechos Infancia Adolescencia Comunitat Valenciana",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-2019-1986_Ley_26-2018_Infancia_CV.pdf",
        boe_pdf_url(2019, "BOE-A-2019-1986"),
        notes="Fuente sectorial candidata para infancia y adolescencia.",
    ),
]


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "GVAdicto/0.1"})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def main() -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for source in SOURCES:
        local_path = ROOT / source.path
        local_path.parent.mkdir(parents=True, exist_ok=True)
        status = "descargado"
        try:
            data = fetch(source.url)
            if not data.startswith(b"%PDF"):
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
                "mime_type": "application/pdf",
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
