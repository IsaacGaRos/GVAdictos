from __future__ import annotations

import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.db import connect, init_db


ROOT = Path(__file__).resolve().parents[1]
CONVOCATORIA_DIR = ROOT / "data" / "sources" / "convocatorias" / "A1-01_2025"
TOPICS_CSV = CONVOCATORIA_DIR / "a1_01_2025_temario_oficial_extraido.csv"
COVERAGE_CSV = CONVOCATORIA_DIR / "a1_01_2025_cobertura_normativa.csv"
AUDIT_CSV = CONVOCATORIA_DIR / "a1_01_2025_topic_validation_audit.csv"
FINDING_SOURCE = "validacion_a1_topic_validation_script"
AUTENTICA_DRIVE_ID = "1Q6XMRE4kdwTL9Wadgmc5iwmuQWUcIEyZ"
AUTENTICA_DRIVE_URL = f"https://drive.google.com/file/d/{AUTENTICA_DRIVE_ID}/view"


@dataclass(frozen=True)
class Mapping:
    drive_topic_number: int
    law_name: str
    normative_reference: str
    mapping_basis: str = "inferencia_texto_temario_pendiente_validacion"
    priority: str = "alta"
    notes: str = ""


@dataclass(frozen=True)
class Finding:
    drive_topic_number: int
    finding_type: str
    severity: str
    description: str


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def split_refs(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"\s*[|;]\s*", value or "") if part.strip()]


def split_topic_numbers(value: str) -> list[int]:
    topic_numbers = []
    for part in re.split(r"\s*,\s*", value or ""):
        if not part:
            continue
        topic_numbers.append(int(part))
    return topic_numbers


def law_id_by_name(conn, law_name: str) -> int | None:
    row = conn.execute("SELECT id FROM laws WHERE name = ? ORDER BY id DESC LIMIT 1", (law_name,)).fetchone()
    if row:
        return int(row["id"])
    return None


def upsert_topic(conn, row: dict[str, str]) -> int:
    drive_topic_number = int(row["drive_topic_number"])
    topic_number = int(row["topic_number"])
    part = "general" if drive_topic_number <= 15 else "especial"
    conn.execute(
        """
        INSERT INTO topics(
            drive_topic_number, topic_number, part, section,
            official_text, normative_refs_raw, validation_status, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'pendiente_de_validacion', CURRENT_TIMESTAMP)
        ON CONFLICT(drive_topic_number) DO UPDATE SET
            topic_number = excluded.topic_number,
            part = excluded.part,
            section = excluded.section,
            official_text = excluded.official_text,
            normative_refs_raw = excluded.normative_refs_raw,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            drive_topic_number,
            topic_number,
            part,
            row["section"],
            row["topic_text"],
            row.get("normative_refs_raw", ""),
        ),
    )
    return int(conn.execute("SELECT id FROM topics WHERE drive_topic_number = ?", (drive_topic_number,)).fetchone()["id"])


def insert_topic_source(
    conn,
    topic_id: int,
    law_id: int | None,
    normative_reference: str,
    coverage_status: str,
    mapping_basis: str,
    priority: str,
    notes: str,
) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO topic_sources(
            topic_id, law_id, normative_reference, coverage_status, mapping_basis,
            priority, validation_status, notes, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'pendiente_de_validacion', ?, CURRENT_TIMESTAMP)
        """,
        (topic_id, law_id, normative_reference, coverage_status, mapping_basis, priority, notes),
    )
    conn.execute(
        """
        UPDATE topic_sources
        SET coverage_status = ?, priority = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
        WHERE topic_id = ?
          AND ((law_id IS NULL AND ? IS NULL) OR law_id = ?)
          AND normative_reference = ?
          AND mapping_basis = ?
        """,
        (coverage_status, priority, notes, topic_id, law_id, law_id, normative_reference, mapping_basis),
    )


def insert_finding(conn, topic_id: int, finding: Finding) -> None:
    conn.execute(
        """
        INSERT INTO topic_validation_findings(
            topic_id, finding_type, severity, status, description, source, updated_at
        ) VALUES (?, ?, ?, 'abierto', ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(topic_id, finding_type, description) DO UPDATE SET
            severity = excluded.severity,
            status = 'abierto',
            source = excluded.source,
            updated_at = CURRENT_TIMESTAMP
        """,
        (topic_id, finding.finding_type, finding.severity, finding.description, FINDING_SOURCE),
    )


def add(mapping_list: list[Mapping], topic: int, law: str, ref: str, notes: str = "") -> None:
    mapping_list.append(Mapping(topic, law, ref, notes=notes))


def add_autentica(mapping_list: list[Mapping], topic: int, law: str, ref: str, notes: str = "") -> None:
    mapping_list.append(
        Mapping(
            topic,
            law,
            ref,
            mapping_basis="autentica_auxiliar_pendiente_validacion",
            priority="media",
            notes=notes or "Indicacion auxiliar de Autentica; requiere contraste con fuente oficial y validacion juridica.",
        )
    )


def inferred_mappings() -> list[Mapping]:
    mappings: list[Mapping] = []

    for topic in [1, 2, 3, 4, 5, 16, 46]:
        add(mappings, topic, "Constitucion Espanola 1978", "Constitucion Espanola 1978")
    for topic in [2, 3]:
        add(mappings, topic, "Ley 50/1997 Gobierno", "Ley 50/1997, de 27 de noviembre, del Gobierno")
    for topic in [3, 28, 29, 30, 31, 33, 34]:
        add(mappings, topic, "Ley 40/2015 Regimen Juridico Sector Publico", "Ley 40/2015, de 1 de octubre, de regimen juridico del sector publico")
    for topic in [19, 20, 24, 25, 26, 27, 30, 31, 34]:
        add(mappings, topic, "Ley 39/2015 Procedimiento Administrativo Comun", "Ley 39/2015, de 1 de octubre, del procedimiento administrativo comun")
    for topic in [4, 18, 22]:
        add(mappings, topic, "Ley Organica 6/1985 Poder Judicial", "Ley Organica 6/1985, de 1 de julio, del Poder Judicial")
    for topic in [4, 23]:
        add(mappings, topic, "Ley Organica 2/1979 Tribunal Constitucional", "Ley Organica 2/1979, de 3 de octubre, del Tribunal Constitucional")
    add(mappings, 4, "Ley Organica 3/1981 Defensor del Pueblo", "Ley Organica 3/1981, de 6 de abril, del Defensor del Pueblo")
    for topic in [3, 51, 62]:
        add(mappings, topic, "Ley Organica 2/1982 Tribunal de Cuentas", "Ley Organica 2/1982, de 12 de mayo, del Tribunal de Cuentas")
    add(mappings, 62, "Ley 7/1988 Funcionamiento Tribunal de Cuentas", "Ley 7/1988, de 5 de abril, de Funcionamiento del Tribunal de Cuentas")

    for topic in [5, 6, 7, 8, 16, 54, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75]:
        add(mappings, topic, "Ley Organica 5/1982 Estatuto Autonomia Comunitat Valenciana", "Ley Organica 5/1982, de 1 de julio, de Estatuto de Autonomia de la Comunidad Valenciana")
    add(mappings, 8, "Ley Organica 5/1985 Regimen Electoral General", "Ley Organica 5/1985, de 19 de junio, del Regimen Electoral General")
    add(mappings, 8, "Ley 1/1987 Electoral Valenciana", "Ley 1/1987, de 31 de marzo, Electoral Valenciana")
    add(mappings, 8, "Ley 5/1983 Gobierno Valenciano Consell", "Ley 5/1983, de 30 de diciembre, del Consell")

    for law in [
        "Ley 2/2021 Sindic de Greuges Comunitat Valenciana",
        "Ley 6/1985 Sindicatura de Cuentas",
        "Ley 10/1994 Consell Juridic Consultiu Comunitat Valenciana",
        "Ley 12/1985 Consell Valencia de Cultura",
        "Ley 7/1998 Academia Valenciana de la Llengua",
        "Ley 1/2014 Comite Economic i Social Comunitat Valenciana",
    ]:
        add(mappings, 11, law, law)

    for topic in [7, 12, 13, 16, 63, 64, 65]:
        add(mappings, topic, "Tratado de la Union Europea version consolidada 2025-03-15", "Tratado de la Union Europea")
        add(mappings, topic, "Tratado de Funcionamiento de la Union Europea version consolidada 2025-03-15", "Tratado de Funcionamiento de la Union Europea")

    add(mappings, 14, "Ley Organica 3/2007 Igualdad efectiva", "Ley Organica 3/2007, de 22 de marzo, para la igualdad efectiva de mujeres y hombres")
    add(mappings, 14, "Ley 9/2003 Igualdad mujeres y hombres Generalitat", "Ley 9/2003, de 2 de abril, de la Generalitat")
    add(mappings, 14, "Ley 4/2023 Igualdad real personas trans y garantia derechos LGTBI", "Ley 4/2023, de 28 de febrero")
    add(mappings, 15, "Ley Organica 1/2004 Violencia de genero", "Ley Organica 1/2004, de 28 de diciembre")

    add(mappings, 17, "Ley 5/1983 Gobierno Valenciano Consell", "Ley 5/1983, de 30 de diciembre, del Consell")
    for topic in [21, 34, 41, 43]:
        add(mappings, topic, "Ley 6/2024 Generalitat Simplificacion Administrativa", "Ley 6/2024, de 5 de diciembre, de la Generalitat, de simplificacion administrativa")
    add(mappings, 21, "Ley 5/1983 Gobierno Valenciano Consell", "Ley 5/1983, de 30 de diciembre, del Consell")
    add(mappings, 22, "Ley 29/1998 Jurisdiccion Contencioso Administrativa", "Ley 29/1998, de 13 de julio, reguladora de la Jurisdiccion Contencioso-administrativa")

    add(mappings, 32, "Ley 14/2003 Patrimonio Generalitat Valenciana", "Ley 14/2003, de 10 de abril, de Patrimonio de la Generalitat Valenciana")
    for topic in [36, 37, 38]:
        add(mappings, topic, "Ley 9/2017 Contratos Sector Publico", "Ley 9/2017, de 8 de noviembre, de Contratos del Sector Publico")
    add(mappings, 39, "Ley de Expropiacion Forzosa 1954", "Ley de 16 de diciembre de 1954 sobre expropiacion forzosa")
    add(mappings, 39, "Reglamento Ley Expropiacion Forzosa 1957", "Decreto de 26 de abril de 1957 por el que se aprueba el Reglamento de la Ley de Expropiacion Forzosa")
    for topic in [40]:
        add(mappings, topic, "Ley 7/1985 Bases Regimen Local", "Ley 7/1985, de 2 de abril, reguladora de las bases del regimen local")
        add(mappings, topic, "Ley 8/2010 Regimen Local Comunitat Valenciana", "Ley 8/2010, de 23 de junio, de regimen local de la Comunitat Valenciana")
    add(mappings, 42, "Decreto 41/2016 calidad servicios publicos y cartas de servicios consolidado DOGV", "Decreto 41/2016, de 15 de abril, del Consell")

    for topic in [44]:
        add(mappings, topic, "Ley 19/2013 Transparencia Acceso Informacion Buen Gobierno", "Ley 19/2013, de 9 de diciembre, de transparencia, acceso a la informacion publica y buen gobierno")
        add(mappings, topic, "Ley 1/2022 Transparencia Buen Gobierno Comunitat Valenciana", "Ley 1/2022, de 13 de abril, de Transparencia y Buen Gobierno de la Comunitat Valenciana")
        add(mappings, topic, "Ley 4/2023 Participacion Ciudadana Comunitat Valenciana", "Ley 4/2023, de 13 de abril, de Participacion Ciudadana y Fomento del Asociacionismo de la Comunitat Valenciana")
        add(mappings, topic, "Ley Organica 3/2018 Proteccion Datos Derechos Digitales", "Ley Organica 3/2018, de 5 de diciembre, de Proteccion de Datos Personales y garantia de los derechos digitales")
    for topic in [45]:
        add(mappings, topic, "Ley 2/2023 Proteccion Informantes", "Ley 2/2023, de 20 de febrero, reguladora de la proteccion de las personas que informen")
        add(mappings, topic, "Ley 4/2021 Funcion Publica Valenciana", "Ley 4/2021, de 16 de abril, de la Generalitat, de la Funcion Publica Valenciana")
        add(mappings, topic, "Ley 1/2022 Transparencia Buen Gobierno Comunitat Valenciana", "Ley 1/2022, de 13 de abril, de Transparencia y Buen Gobierno de la Comunitat Valenciana")

    add(mappings, 46, "Real Decreto Legislativo 5/2015 TREBEP", "Real Decreto Legislativo 5/2015, de 30 de octubre, por el que se aprueba el TREBEP")
    add(mappings, 47, "Real Decreto Legislativo 8/2015 Ley General Seguridad Social", "Real Decreto Legislativo 8/2015, de 30 de octubre, Ley General de la Seguridad Social")
    for topic in [48, 49, 50, 51, 52]:
        add(mappings, topic, "Ley 4/2021 Funcion Publica Valenciana", "Ley 4/2021, de 16 de abril, de la Generalitat, de la Funcion Publica Valenciana")
        add(mappings, topic, "Real Decreto Legislativo 5/2015 TREBEP", "Real Decreto Legislativo 5/2015, de 30 de octubre, por el que se aprueba el TREBEP")
    add(mappings, 51, "Ley 53/1984 Incompatibilidades Personal Administraciones Publicas", "Ley 53/1984, de 26 de diciembre, de Incompatibilidades")
    add(mappings, 51, "Ley 31/1995 Prevencion Riesgos Laborales", "Ley 31/1995, de 8 de noviembre, de Prevencion de Riesgos Laborales")
    add(mappings, 53, "Real Decreto Legislativo 2/2015 Estatuto Trabajadores", "Real Decreto Legislativo 2/2015, de 23 de octubre, Estatuto de los Trabajadores")

    add(mappings, 54, "Ley Organica 8/1980 Financiacion Comunidades Autonomas", "Ley Organica 8/1980, de 22 de septiembre, de Financiacion de las Comunidades Autonomas")
    add(mappings, 54, "Ley 22/2009 Sistema Financiacion Comunidades Autonomas", "Ley 22/2009, de 18 de diciembre, sistema de financiacion de las Comunidades Autonomas")
    add(mappings, 55, "Ley Organica 2/2012 Estabilidad Presupuestaria", "Ley Organica 2/2012, de 27 de abril, de Estabilidad Presupuestaria")
    for topic in [55, 56, 57, 58, 59, 61, 62]:
        add(mappings, topic, "Ley 1/2015 Generalitat Hacienda Publica Sector Publico Instrumental y Subvenciones", "Ley 1/2015, de 6 de febrero, de hacienda publica, sector publico instrumental y subvenciones")
    for topic in [57, 58]:
        add(mappings, topic, "Ley 6/2025 Presupuestos Generalitat 2025", "Ley de presupuestos de la Generalitat vigente")
        add(mappings, topic, "Decreto 204/2025 prorroga automatica presupuestos Generalitat 2025 para 2026", "Decreto 204/2025, de prorroga automatica de presupuestos")
    add(mappings, 60, "Ley 20/2017 Tasas Generalitat", "Ley 20/2017, de 28 de diciembre, de tasas")
    add(mappings, 60, "Decreto 103/2014 Precios Publicos Generalitat", "Decreto 103/2014, de 4 de julio, del Consell")

    add(mappings, 66, "Ley 3/2019 Servicios Sociales Inclusivos Comunitat Valenciana", "Ley 3/2019, de servicios sociales inclusivos de la Comunitat Valenciana")
    add(mappings, 66, "Ley 26/2018 Derechos Infancia Adolescencia Comunitat Valenciana", "Ley 26/2018, de derechos y garantias de la infancia y adolescencia")

    return mappings


def autentica_auxiliary_mappings() -> list[Mapping]:
    mappings: list[Mapping] = []

    add_autentica(mappings, 8, "Reglamento de Les Corts consolidado DOGV", "Reglamento de Les Corts: titulos V y VI")
    add_autentica(mappings, 18, "Ley Organica 2/1987 Conflictos Jurisdiccionales", "Ley Organica 2/1987, de 18 de mayo, de Conflictos Jurisdiccionales")
    add_autentica(mappings, 21, "Ley 39/2015 Procedimiento Administrativo Comun", "Ley 39/2015: titulo VI")
    add_autentica(mappings, 21, "Ley 1/2022 Transparencia Buen Gobierno Comunitat Valenciana", "Ley 1/2022: titulo IV, capitulo II")
    add_autentica(mappings, 23, "Ley Organica 2/1979 Tribunal Constitucional", "LOTC: capitulo I del titulo I, titulos II, III, IV, V y VI bis")
    add_autentica(mappings, 32, "Ley 33/2003 Patrimonio Administraciones Publicas", "Ley 33/2003, de Patrimonio de las Administraciones Publicas")

    add_autentica(mappings, 41, "Carta de Derechos Fundamentales de la Union Europea", "Carta de Derechos Fundamentales UE: articulo 41")
    add_autentica(mappings, 44, "Ley 25/2018 Grupos de Interes Comunitat Valenciana", "Ley 25/2018, de grupos de interes de la Comunitat Valenciana")
    add_autentica(mappings, 44, "Reglamento UE 2016/679 Proteccion Datos RGPD", "Reglamento UE 2016/679, RGPD")
    add_autentica(mappings, 45, "Ley 8/2016 Incompatibilidades Conflictos Intereses Cargos Publicos CV", "Ley 8/2016, conflictos de intereses de cargos publicos no electos")
    add_autentica(mappings, 45, "Reglamento UE Euratom 2024/2509 Normas financieras presupuesto UE", "Reglamento financiero UE vigente: conflicto de interes")

    add_autentica(mappings, 50, "Decreto 3/2017 Seleccion Provision Movilidad Funcion Publica Valenciana", "Decreto 3/2017, seleccion, provision y movilidad")
    add_autentica(mappings, 50, "Decreto 49/2021 Teletrabajo Generalitat", "Decreto 49/2021, teletrabajo")
    add_autentica(mappings, 51, "Decreto 42/2019 Condiciones Trabajo Personal Funcionario Generalitat consolidado DOGV", "Decreto 42/2019, condiciones de trabajo")
    add_autentica(mappings, 51, "Real Decreto 33/1986 Regimen Disciplinario Funcionarios", "Real Decreto 33/1986, regimen disciplinario")
    add_autentica(mappings, 51, "Ley Organica 2/1982 Tribunal de Cuentas", "Ley Organica 2/1982: titulo IV")

    add_autentica(mappings, 54, "Ley 13/1997 Tramo autonomico IRPF y tributos cedidos CV", "Ley 13/1997, tramo autonomico IRPF y tributos cedidos")
    add_autentica(mappings, 54, "Ley 22/2001 Fondos de Compensacion Interterritorial", "Ley 22/2001, fondos de compensacion interterritorial")
    add_autentica(mappings, 55, "Real Decreto 635/2014 Periodo Medio Pago Proveedores", "Real Decreto 635/2014, periodo medio de pago a proveedores")
    add_autentica(mappings, 58, "Decreto 25/2017 Fondos de Caja Fija", "Decreto 25/2017, fondos de caja fija")
    add_autentica(mappings, 58, "Orden 18/2023 NEFIS", "Orden 18/2023, NEFIS")
    add_autentica(mappings, 58, "Orden 27 diciembre 2001 Clasificacion Economica Generalitat", "Orden de 27 de diciembre de 2001, clasificacion economica")

    for topic in [63, 64, 65]:
        add_autentica(mappings, topic, "Carta de Derechos Fundamentales de la Union Europea", "Carta de Derechos Fundamentales de la Union Europea")

    return mappings


def validation_findings() -> list[Finding]:
    findings = [
        Finding(8, "delimitacion_articulos_pendiente", "media", "Autentica apunta Reglamento de Les Corts titulos V y VI; fuente DOGV incorporada, pendiente validacion juridica de articulos exactos."),
        Finding(17, "delimitacion_articulos_pendiente", "media", "Tema doctrinal sobre potestad reglamentaria: requiere seleccion manual de articulos concretos en Constitucion, Ley 39/2015, Ley 40/2015, Ley 50/1997 y Ley 5/1983."),
        Finding(18, "delimitacion_articulos_pendiente", "media", "Autentica apunta LO 2/1987 de conflictos jurisdiccionales; fuente BOE incorporada, pendiente validar articulos exactos."),
        Finding(21, "delimitacion_articulos_pendiente", "media", "Requiere validar articulos concretos de iniciativa legislativa, potestad reglamentaria, calidad normativa y programacion en normativa estatal/autonomica."),
        Finding(32, "delimitacion_articulos_pendiente", "media", "Autentica apunta Ley 33/2003 para legislacion basica estatal de patrimonio; fuente BOE incorporada, pendiente validar preceptos basicos aplicables."),
        Finding(33, "tema_doctrinal_pendiente", "media", "Tema de formas de actividad administrativa requiere matriz doctrinal con fuentes normativas parciales antes de generar preguntas sustantivas."),
        Finding(41, "fuente_no_normativa_pendiente", "media", "Gobernanza, Libro Blanco UE y Agenda 2030 requieren fuentes institucionales no estrictamente normativas para estudiar sin mezclar con leyes."),
        Finding(41, "fuente_eurlex_pendiente", "alta", "Autentica apunta Carta de Derechos Fundamentales UE art. 41; pendiente ajustar descarga EUR-Lex/Publication Office para importacion automatica."),
        Finding(43, "tema_doctrinal_pendiente", "media", "Planificacion estrategica requiere seleccionar normativa estatal/autonomica aplicable y fuentes tecnicas antes de generar preguntas."),
        Finding(44, "fuente_eurlex_pendiente", "alta", "Autentica apunta RGPD; pendiente ajustar descarga EUR-Lex/Publication Office para importacion automatica y control de version."),
        Finding(45, "fuente_europea_pendiente", "alta", "Autentica cita Reglamento UE 2018/1046; se ha identificado como sustituido por Reglamento UE/Euratom 2024/2509, pendiente importacion EUR-Lex y validacion juridica."),
        Finding(50, "fuente_reglamentaria_pendiente", "media", "Autentica apunta Decreto 3/2017 y Decreto 49/2021; fuentes DOGV incorporadas, pendiente comprobar consolidacion y articulos exactos."),
        Finding(51, "fuente_reglamentaria_pendiente", "media", "Autentica apunta Decreto 42/2019 y RD 33/1986; fuentes incorporadas, pendiente comprobar consolidacion y articulos exactos."),
        Finding(52, "delimitacion_articulos_pendiente", "media", "Representacion y negociacion colectiva requiere delimitar TREBEP/LFPV y posible normativa laboral aplicable."),
        Finding(54, "delimitacion_articulos_pendiente", "alta", "Autentica apunta Ley 13/1997 y Ley 22/2001 ademas de LOFCA, Ley 22/2009 y Estatuto CV; fuentes BOE incorporadas, pendiente articulado exacto."),
        Finding(55, "delimitacion_articulos_pendiente", "media", "Autentica apunta RD 635/2014 para periodo medio de pago a proveedores; fuente BOE incorporada, pendiente articulos exactos."),
        Finding(58, "fuente_complementaria_pendiente", "media", "Autentica apunta Decreto 25/2017, Orden 18/2023 NEFIS y Orden de 27/12/2001; fuentes incorporadas salvo validacion fina de vigencia y articulado."),
    ]
    for topic in range(67, 76):
        findings.append(
            Finding(
                topic,
                "sectorial_sources_pending",
                "alta",
                "Tema de competencias sectoriales de la Generalitat: se ha enlazado el Estatuto CV, pero falta matriz de principales normas sectoriales vigentes antes de cerrar validacion.",
            )
        )
    return findings


def import_topics_and_coverage() -> dict[str, int]:
    init_db()
    topics = read_csv(TOPICS_CSV)
    coverage_rows = read_csv(COVERAGE_CSV)
    summary = {
        "topics": 0,
        "explicit_mappings": 0,
        "inferred_mappings": 0,
        "autentica_mappings": 0,
        "findings": 0,
        "missing_laws": 0,
    }

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO source_documents(
                source_kind, external_id, title, path, mime_type, url,
                priority, status, legal_status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_kind, external_id) DO UPDATE SET
                title = excluded.title,
                path = excluded.path,
                mime_type = excluded.mime_type,
                url = excluded.url,
                priority = excluded.priority,
                status = excluded.status,
                legal_status = excluded.legal_status,
                notes = excluded.notes
            """,
            (
                "google_drive_autentica",
                AUTENTICA_DRIVE_ID,
                "Legislacion A1 2025 v4.pdf",
                "Mi Unidad/Opo/Autentica/Legislacion A1 2025 v4.pdf",
                "application/pdf",
                AUTENTICA_DRIVE_URL,
                "media",
                "catalogado",
                "auxiliar_no_oficial",
                "Usado solo como contraste de cobertura normativa; no fuente juridica oficial.",
            ),
        )
        topic_ids: dict[int, int] = {}
        for row in topics:
            topic_id = upsert_topic(conn, row)
            topic_ids[int(row["drive_topic_number"])] = topic_id
            summary["topics"] += 1

        conn.execute(
            """
            DELETE FROM topic_sources
            WHERE mapping_basis IN (
                'explicit_coverage_csv',
                'inferencia_texto_temario_pendiente_validacion',
                'autentica_auxiliar_pendiente_validacion'
            )
            """
        )
        conn.execute("DELETE FROM topic_validation_findings WHERE source = ?", (FINDING_SOURCE,))

        for row in coverage_rows:
            law_names = split_refs(row.get("local_law_name", ""))
            for drive_topic_number in split_topic_numbers(row.get("topics", "")):
                topic_id = topic_ids.get(drive_topic_number)
                if not topic_id:
                    continue
                for law_name in law_names:
                    law_id = law_id_by_name(conn, law_name)
                    if law_id is None:
                        summary["missing_laws"] += 1
                        insert_finding(
                            conn,
                            topic_id,
                            Finding(
                                drive_topic_number,
                                "local_law_name_no_encontrado",
                                "alta",
                                f"No se ha encontrado en SQLite la norma indicada en cobertura inicial: {law_name}",
                            ),
                        )
                    insert_topic_source(
                        conn,
                        topic_id,
                        law_id,
                        row.get("normative_reference", law_name),
                        row.get("coverage_status", "pendiente_de_validacion"),
                        "explicit_coverage_csv",
                        "alta",
                        "Referencia expresa extraida de la correccion oficial del temario A1-01 2025.",
                    )
                    summary["explicit_mappings"] += 1

        for mapping in inferred_mappings():
            topic_id = topic_ids.get(mapping.drive_topic_number)
            if not topic_id:
                continue
            law_id = law_id_by_name(conn, mapping.law_name)
            if law_id is None:
                summary["missing_laws"] += 1
                insert_finding(
                    conn,
                    topic_id,
                    Finding(
                        mapping.drive_topic_number,
                        "fuente_oficial_no_importada",
                        "alta",
                        f"Norma inferida del epigrafe pendiente de importar o revisar en SQLite: {mapping.law_name}",
                    ),
                )
            insert_topic_source(
                conn,
                topic_id,
                law_id,
                mapping.normative_reference,
                "pendiente_de_validacion",
                mapping.mapping_basis,
                mapping.priority,
                mapping.notes or "Mapeo inferido del enunciado oficial; requiere validacion juridica.",
            )
            summary["inferred_mappings"] += 1

        for mapping in autentica_auxiliary_mappings():
            topic_id = topic_ids.get(mapping.drive_topic_number)
            if not topic_id:
                continue
            law_id = law_id_by_name(conn, mapping.law_name)
            if law_id is None:
                summary["missing_laws"] += 1
                insert_finding(
                    conn,
                    topic_id,
                    Finding(
                        mapping.drive_topic_number,
                        "autentica_fuente_oficial_no_importada",
                        "alta",
                        f"Autentica apunta una norma no importada automaticamente: {mapping.law_name}",
                    ),
                )
            insert_topic_source(
                conn,
                topic_id,
                law_id,
                mapping.normative_reference,
                "pendiente_de_validacion",
                mapping.mapping_basis,
                mapping.priority,
                mapping.notes,
            )
            summary["autentica_mappings"] += 1

        for finding in validation_findings():
            topic_id = topic_ids.get(finding.drive_topic_number)
            if topic_id:
                insert_finding(conn, topic_id, finding)
                summary["findings"] += 1

        conn.execute(
            """
            UPDATE topics
            SET validation_status = CASE
                WHEN EXISTS (
                    SELECT 1 FROM topic_validation_findings f
                    WHERE f.topic_id = topics.id AND f.status = 'abierto'
                ) THEN 'requiere_revision_fuentes'
                ELSE 'pendiente_de_validacion'
            END,
            updated_at = CURRENT_TIMESTAMP
            """
        )

        audit_rows = conn.execute(
            """
            SELECT
                t.drive_topic_number,
                t.topic_number,
                t.part,
                t.section,
                t.validation_status,
                t.official_text,
                COALESCE(GROUP_CONCAT(DISTINCT l.name), '') AS mapped_laws,
                COUNT(DISTINCT f.id) AS findings_count,
                COALESCE(GROUP_CONCAT(DISTINCT f.description), '') AS open_findings,
                COALESCE(t.notes, '') AS notes
            FROM topics t
            LEFT JOIN topic_sources ts ON ts.topic_id = t.id
            LEFT JOIN laws l ON l.id = ts.law_id
            LEFT JOIN topic_validation_findings f ON f.topic_id = t.id AND f.status = 'abierto'
            GROUP BY t.id
            ORDER BY t.drive_topic_number
            """
        ).fetchall()

    with AUDIT_CSV.open("w", encoding="utf-8", newline="") as fh:
        fieldnames = [
            "drive_topic_number",
            "topic_number",
            "part",
            "section",
            "validation_status",
            "official_text",
            "mapped_laws",
            "findings_count",
            "open_findings",
            "notes",
        ]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([dict(row) for row in audit_rows])

    summary["findings"] = sum(1 for row in audit_rows if int(row["findings_count"]) > 0)
    return summary


def main() -> None:
    summary = import_topics_and_coverage()
    print(summary)
    print(f"Audit written: {AUDIT_CSV}")


if __name__ == "__main__":
    main()
