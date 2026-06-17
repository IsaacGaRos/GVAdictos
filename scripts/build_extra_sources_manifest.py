from __future__ import annotations

import csv
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data" / "sources" / "official_normative_sources_extra.csv"


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


SOURCES: list[Source] = [
    Source(
        "boe_consolidado",
        "BOE-A-2015-1952",
        "Ley 1/2015 Generalitat Hacienda Publica Sector Publico Instrumental y Subvenciones",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-2015-1952_Ley_1-2015_Hacienda_Publica_Generalitat.pdf",
        "https://www.boe.es/buscar/pdf/2015/BOE-A-2015-1952-consolidado.pdf",
        notes="Texto consolidado BOE; caracter informativo.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-2021-8880",
        "Ley 4/2021 Funcion Publica Valenciana",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-2021-8880_Ley_4-2021_Funcion_Publica_Valenciana.pdf",
        "https://www.boe.es/buscar/pdf/2021/BOE-A-2021-8880-consolidado.pdf",
        notes="Texto consolidado BOE; caracter informativo.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-2023-5366",
        "Ley 4/2023 Igualdad real personas trans y garantia derechos LGTBI",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-2023-5366_Ley_4-2023_Trans_LGTBI.pdf",
        "https://www.boe.es/buscar/pdf/2023/BOE-A-2023-5366-consolidado.pdf",
        notes="Texto consolidado BOE; caracter informativo.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-1984-3460",
        "Ley 5/1983 Gobierno Valenciano Consell",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-1984-3460_Ley_5-1983_Consell.pdf",
        "https://www.boe.es/buscar/pdf/1984/BOE-A-1984-3460-consolidado.pdf",
        notes="Texto consolidado BOE; la norma aparece como Ley 5/1983 de Gobierno Valenciano.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-2025-1",
        "Ley 6/2024 Generalitat Simplificacion Administrativa",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-2025-1_Ley_6-2024_Simplificacion_Administrativa.pdf",
        "https://www.boe.es/buscar/pdf/2025/BOE-A-2025-1-consolidado.pdf",
        notes="Texto consolidado BOE; caracter informativo.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-2010-11729",
        "Ley 8/2010 Regimen Local Comunitat Valenciana",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-2010-11729_Ley_8-2010_Regimen_Local_CV.pdf",
        "https://www.boe.es/buscar/pdf/2010/BOE-A-2010-11729-consolidado.pdf",
        notes="Texto consolidado BOE; caracter informativo.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-2003-9334",
        "Ley 9/2003 Igualdad mujeres y hombres Generalitat",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-2003-9334_Ley_9-2003_Igualdad_Mujeres_Hombres.pdf",
        "https://www.boe.es/buscar/pdf/2003/BOE-A-2003-9334-consolidado.pdf",
        notes="Texto consolidado BOE; caracter informativo.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-2003-10298",
        "Ley 14/2003 Patrimonio Generalitat Valenciana",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-2003-10298_Ley_14-2003_Patrimonio_Generalitat.pdf",
        "https://www.boe.es/buscar/pdf/2003/BOE-A-2003-10298-consolidado.pdf",
        notes="Texto consolidado BOE; caracter informativo.",
    ),
    Source(
        "boe_consolidado",
        "BOE-A-2018-1870",
        "Ley 20/2017 Tasas Generalitat",
        "data/sources/leyes_originales/BOE_consolidadas/BOE-A-2018-1870_Ley_20-2017_Tasas_Generalitat.pdf",
        "https://www.boe.es/buscar/pdf/2018/BOE-A-2018-1870-consolidado.pdf",
        notes="Texto consolidado BOE; caracter informativo.",
    ),
    Source(
        "boe_pdf",
        "BOE-A-2025-11960",
        "Ley 6/2025 Presupuestos Generalitat 2025",
        "data/sources/leyes_originales/BOE/BOE-A-2025-11960_Ley_6-2025_Presupuestos_Generalitat_2025.pdf",
        "https://www.boe.es/boe/dias/2025/06/14/pdfs/BOE-A-2025-11960.pdf",
        notes="Ley de presupuestos 2025; en 2026 se encuentra prorrogada salvo aprobacion posterior.",
    ),
    Source(
        "dogv_pdf",
        "DOGV-C-2025-52312",
        "Decreto 204/2025 prorroga automatica presupuestos Generalitat 2025 para 2026",
        "data/sources/leyes_originales/DOGV/DOGV-C-2025-52312_Decreto_204-2025_Prorroga_Presupuestos_2026.pdf",
        "https://dogv.gva.es/datos/2025/12/31/pdf/2025_52312_es.pdf",
        notes="Norma auxiliar para constatar la prorroga presupuestaria 2026.",
    ),
    Source(
        "dogv_pdf",
        "DOGV-2014-6339",
        "Decreto 103/2014 Precios Publicos Generalitat",
        "data/sources/leyes_originales/DOGV/DOGV-2014-6339_Decreto_103-2014_Precios_Publicos.pdf",
        "https://dogv.gva.es/datos/2014/07/07/pdf/2014_6339.pdf",
        notes="DOGV original; pendiente comprobar si existe texto consolidado oficial.",
    ),
    Source(
        "dogv_pdf",
        "DOGV-2017-9301",
        "Decreto 128/2017 ayudas publicas Generalitat notificacion Comision Europea",
        "data/sources/leyes_originales/DOGV/DOGV-2017-9301_Decreto_128-2017_Ayudas_Publicas.pdf",
        "https://dogv.gva.es/datos/2017/10/20/pdf/2017_9301.pdf",
        notes="DOGV original; pendiente comprobar si existe texto consolidado oficial.",
    ),
    Source(
        "dogv_pdf",
        "DOGV-D-2014-176-CONS",
        "Decreto 176/2014 convenios Generalitat consolidado DOGV",
        "data/sources/leyes_originales/DOGV/DOGV-D_2014_176_ca_DL_2022_01_Decreto_176-2014_Convenios.pdf",
        "https://dogv.gva.es/datos/consolidacion/2014/D_2014_176_ca_DL_2022_01.pdf",
        notes="Legislacion consolidada DOGV.",
    ),
    Source(
        "dogv_pdf",
        "DOGV-D-2016-041-CONS",
        "Decreto 41/2016 calidad servicios publicos y cartas de servicios consolidado DOGV",
        "data/sources/leyes_originales/DOGV/DOGV-D_2016_041_ca_D_2024_053_Decreto_41-2016.pdf",
        "https://dogv.gva.es/datos/consolidacion/2016/D_2016_041_ca_D_2024_053.pdf",
        notes="Legislacion consolidada DOGV.",
    ),
    Source(
        "dogv_pdf",
        "DOGV-C-2025-11622",
        "Decreto 54/2025 simplificacion administrativa y transformacion digital",
        "data/sources/leyes_originales/DOGV/DOGV-C-2025-11622_Decreto_54-2025_Simplificacion_Transformacion_Digital.pdf",
        "https://dogv.gva.es/datos/2025/04/22/pdf/2025_11622_es.pdf",
        notes="DOGV original; se importa tambien Decreto-ley 14/2025 por modificaciones posteriores.",
    ),
    Source(
        "dogv_pdf",
        "DOGV-C-2025-52316",
        "Decreto-ley 14/2025 hiperregulacion agilizacion procedimientos unidad mercado",
        "data/sources/leyes_originales/DOGV/DOGV-C-2025-52316_Decreto_Ley_14-2025_Hiperregulacion.pdf",
        "https://dogv.gva.es/datos/2025/12/29/pdf/2025_52316_es.pdf",
        notes="Modifica, entre otras, Ley 4/2021, Ley 6/2024, Decreto 54/2025 y Ley 20/2017.",
    ),
]


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "GVAdicto/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response:
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
