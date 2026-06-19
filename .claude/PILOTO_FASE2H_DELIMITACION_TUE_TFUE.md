# Fase 2H - Delimitacion fina TUE/TFUE para PE-48/49/50

Autor: Claude Code (Sonnet 4.6)
Fecha: 2026-06-18
Nivel de rigor: extremadamente alto
Estado: pendiente de ejecucion

## Contexto

Survey sobre los 416 articulos de TUE (law_id=34, 81 arts) y TFUE (law_id=35, 335 arts)
importados de EUR-Lex consolidado 2025-03-15.

Objetivo: delimitar los articulos concretos de TUE/TFUE relevantes para los temas:

| topic_id | drive_num | num | Enunciado (extracto) |
|---|---|---|---|
| 63 | 63 | 48 | Caracteristicas del ordenamiento juridico UE. Fuentes del DUE. Tratados constitutivos. Actos juridicos: reglamentos, directivas, decisiones, recomendaciones y dictamenes. |
| 64 | 64 | 49 | Derechos fundamentales y ciudadania de la Union. Mercado interior: libre circulacion de mercancias, trabajadores, personas, servicios y capitales. Competencias y garantias sobre el espacio de libertad, seguridad y justicia. |
| 65 | 65 | 50 | Derecho de la Union Europea. El Derecho Primario y el Derecho Derivado. Jerarquia de las normas. La relacion entre el DUE y el ordenamiento juridico de los Estados Miembros. Principios y control. La participacion de las Comunidades Autonomas y de la Generalitat en la formacion y en la ejecucion del derecho de la Union Europea. |

## Hallazgo critico: articulos de protocolo mezclados

El parser del HTML EUR-Lex capturo articulos de los Protocolos anejos al TUE/TFUE
con los mismos numeros de referencia (1, 2, 3...) que los articulos del tratado principal.
Esto contamina las siguientes referencias en la BD:

TUE arts con contenido incorrecto (protocolo): 1, 2, 3, 4, 5, 7, 8, 13, 47
- Art. 1: "operaciones de liquidacion" → Protocolo EIB Estatuto
- Art. 2: "legislatura 2009-2014" → Protocolo 36 Disposiciones Transitorias
- Art. 3: "articulo 16 TUE... articulo 238 TFUE" → Protocolo 36
- Art. 4: "Antillas neerlandesas" → Protocolo Territorios de Ultramar
- Art. 5: "acervo de Schengen" → Protocolo Schengen
- Art. 7: contenido sobre subsidiariedad de Protocolo 2
- Art. 8: "Dinamarca" → Protocolo Dinamarca
- Art. 13: "impuestos sobre la renta" → Protocolo sobre Privilegios
- Art. 47: referencia cruzada → Protocolo

TFUE arts con contenido incorrecto (protocolo): 2, 3, 4, 5, 6, 18, 23, 27, 28, 47, 48
- Arts. 2-6: Protocolos de transicion y Schengen
- Art. 18: "operaciones de financiacion del Banco" → Estatuto EIB
- Arts. 27-28: EIB Estatuto arts 27-28
- Arts. 47-48: Estatuto BCE

Consecuencia para la delimitacion:
- NO se pueden usar rangos genericos tipo CAST(article_ref AS INTEGER) BETWEEN 1 AND 10
- El script usa IDs de articulo verificados explicitamente
- Los arts. TUE 1-5 (creation, valores, objetivos, cooperacion leal, subsidiariedad)
  y TUE 47 (personalidad juridica) NO son mapeables con la BD actual
- Para topic 65 (primacia, subsidiariedad), los articulos doctrinales clave
  (TUE 4, 5) son inutilizables en la BD; se mapean solo los procedimentales (TFUE 258-267)
- La participacion de CCAA en asuntos UE no tiene base en TUE/TFUE: materia de derecho
  espanol (LO 2/1997, CARCE, LOTC art. 93). No se mapea en este script.

## Articulos verificados por tema

### Topic 63 (id=63) — Fuentes DUE, tratados constitutivos, actos juridicos

| law_id | Ley | art_ref | article_id | Prioridad | Justificacion |
|---|---|---|---|---|---|
| 34 | TUE | 48 | 102238 | media | Procedimiento revision tratados |
| 35 | TFUE | 288 | 103373 | alta | Definicion reglamentos/directivas/decisiones/recomendaciones/dictamenes |
| 35 | TFUE | 289 | 103374 | alta | Procedimiento legislativo ordinario y especial |
| 35 | TFUE | 290 | 103375 | media | Actos delegados |
| 35 | TFUE | 291 | 103376 | media | Actos de ejecucion |
| 35 | TFUE | 293 | 103378 | baja | Propuestas Comision |
| 35 | TFUE | 294 | 103379 | media | Procedimiento legislativo ordinario (detalle) |
| 35 | TFUE | 296 | 103381 | media | Forma de los actos, motivacion |
| 35 | TFUE | 297 | 103382 | media | Publicacion y entrada en vigor |
| 35 | TFUE | 299 | 103384 | baja | Fuerza ejecutiva |

Total: 10 filas

### Topic 64 (id=64) — Derechos fundamentales, ciudadania, mercado interior, LSJ

| law_id | Ley | art_ref | article_id | Prioridad | Justificacion |
|---|---|---|---|---|---|
| 34 | TUE | 6 | 102196 | alta | Carta DDFFF + CEDH (derechos fundamentales) |
| 34 | TUE | 9 | 102397 | alta | Ciudadania de la Union (principio) |
| 35 | TFUE | 20 | 103105 | alta | Creacion ciudadania UE |
| 35 | TFUE | 21 | 103106 | alta | Libre circulacion y residencia ciudadanos |
| 35 | TFUE | 22 | 103107 | media | Derecho de voto (residencia) |
| 35 | TFUE | 24 | 103109 | media | Peticion, defensor del pueblo |
| 35 | TFUE | 25 | 103110 | baja | Informe ciudadania |
| 35 | TFUE | 26 | 103111 | alta | Mercado interior (definicion y objetivo) |
| 35 | TFUE | 29 | 103114 | media | Union aduanera: libre circulacion |
| 35 | TFUE | 30 | 103115 | alta | Prohibicion derechos aduaneros entre EEMM |
| 35 | TFUE | 31 | 103116 | baja | Arancel aduanero comun |
| 35 | TFUE | 34 | 103119 | alta | Prohibicion restricciones cuantitativas importacion |
| 35 | TFUE | 35 | 103120 | media | Prohibicion restricciones cuantitativas exportacion |
| 35 | TFUE | 36 | 103121 | alta | Excepciones libre circulacion mercancias |
| 35 | TFUE | 45 | 103130 | alta | Libre circulacion de trabajadores |
| 35 | TFUE | 46 | 103131 | media | Medidas legislativas libre circulacion trabajadores |
| 35 | TFUE | 49 | 103134 | alta | Libertad de establecimiento |
| 35 | TFUE | 50 | 103135 | media | Programa general establecimiento |
| 35 | TFUE | 54 | 103139 | baja | Sociedades beneficiarias establecimiento |
| 35 | TFUE | 55 | 103140 | baja | Participacion financiera nacional |
| 35 | TFUE | 56 | 103141 | alta | Libre prestacion de servicios |
| 35 | TFUE | 57 | 103142 | media | Definicion de servicios |
| 35 | TFUE | 62 | 103147 | baja | Establecimiento aplicable a servicios |
| 35 | TFUE | 63 | 103148 | alta | Libre circulacion de capitales |
| 35 | TFUE | 64 | 103149 | media | Circulacion capitales con terceros paises |
| 35 | TFUE | 65 | 103150 | media | Excepciones libre circulacion capitales |
| 35 | TFUE | 66 | 103151 | baja | Medidas de salvaguardia capitales |
| 35 | TFUE | 67 | 103152 | alta | Espacio de libertad, seguridad y justicia (definicion) |
| 35 | TFUE | 77 | 103162 | media | Controles fronterizos, Schengen |
| 35 | TFUE | 78 | 103163 | media | Politica comun asilo |
| 35 | TFUE | 79 | 103164 | media | Politica comun inmigracion |
| 35 | TFUE | 82 | 103167 | media | Cooperacion judicial en materia penal |
| 35 | TFUE | 83 | 103168 | media | Armonizacion delitos y sanciones |
| 35 | TFUE | 87 | 103172 | media | Cooperacion policial |
| 35 | TFUE | 88 | 103173 | media | Europol |
| 35 | TFUE | 89 | 103174 | baja | Operaciones transfronterizas |

Total: 36 filas

Nota: TFUE arts. 47 y 48 (trabajadores) estan CONTAMINADOS en la BD (Protocolo BCE).
No se mapean. Solo se mapean 45 y 46 para la libre circulacion de trabajadores.
TFUE art. 18 (no discriminacion por nacionalidad) tambien contaminado (Estatuto EIB).

### Topic 65 (id=65) — Derecho Primario/Derivado, jerarquia, relacion DUE-EEMM

| law_id | Ley | art_ref | article_id | Prioridad | Justificacion |
|---|---|---|---|---|---|
| 35 | TFUE | 258 | 103343 | alta | Recurso incumplimiento (Comision) |
| 35 | TFUE | 259 | 103344 | media | Recurso incumplimiento (EEMM) |
| 35 | TFUE | 260 | 103345 | media | Consecuencias del incumplimiento |
| 35 | TFUE | 267 | 103352 | alta | Cuestion prejudicial (relacion DUE-Derecho nacional) |
| 35 | TFUE | 288 | 103373 | alta | Derecho derivado: tipologia actos |

Total: 5 filas

Nota: TUE arts. 4 (cooperacion leal) y 5 (subsidiariedad/proporcionalidad) son
esenciales para este tema pero estan CONTAMINADOS en la BD. Se anota como deuda tecnica.
La participacion de CCAA/Generalitat no esta regulada en TUE/TFUE; queda fuera del script.

## Resumen

| Topic | TUE filas | TFUE filas | Total |
|---|---|---|---|
| 63 | 1 | 9 | 10 |
| 64 | 2 | 34 | 36 |
| 65 | 0 | 5 | 5 |
| TOTAL | 3 | 48 | 51 |

## Script

```powershell
python scripts/apply_fase2h_tue_tfue_delimitation.py
python scripts/apply_fase2h_tue_tfue_delimitation.py --apply
```

mapping_basis: `delimitacion_fina_claude_fase2h_tue_tfue_2026_06_18`

## Deuda tecnica registrada

1. TUE arts. 1-8, 13, 16, 18, 19, 47 y TFUE arts. 2-6, 18, 23, 27, 28, 47, 48
   contienen contenido de Protocolos anejos (Estatuto EIB, Estatuto BCE, Protocolo
   Schengen, Disposiciones Transitorias). Requieren reimportacion selectiva del
   TUE/TFUE principal (solo TITULO + PARTES, sin Protocolos) para ser usables.
2. Hasta que se reimporte, topic 65 carece de TUE 4 (cooperacion leal) y TUE 5
   (subsidiariedad), que son los articulos doctrinales mas relevantes para ese tema.

## Continuacion 2H (2026-06-18): gen-12 y gen-13

Tras completar PE-48/49/50, se evaluaron los dos temas restantes del bloque UE:

### gen-12 (topic_id=12) — Instituciones y organismos UE — DELIMITADO

Cobertura solida via TFUE. Articulos limpios usados:
- Parlamento: TUE 14 + TFUE 223-234
- Consejo Europeo: TUE 15 + TFUE 235
- Consejo UE: TFUE 237-243 (TUE 16 contaminado-EIB, excluido)
- Comision: TUE 17 + TFUE 245-250
- TJUE: TFUE 251-257, 263, 265, 267, 268, 281 (TUE 19 contaminado-EIB, excluido)
- BCE: TFUE 282-284
- Tribunal de Cuentas: TFUE 285-287
- CESE: TFUE 300-304
- Comite de las Regiones: TFUE 305-307

Script: `scripts/apply_fase2h_gen12_instituciones_delimitation.py`
mapping_basis: `delimitacion_fina_claude_fase2h_gen12_instituciones_2026_06_18`
Resultado: 54 filas insertadas, FK=0, validate_article_quality PASS.
Backup: `db/gvadicto.backup_pre2h_gen12_20260618_232521.sqlite`

### gen-13 (topic_id=13) — Naturaleza, valores, objetivos, miembros, competencias — BLOQUEADO

NO delimitado. Los articulos sustantivos del tema estan TODOS contaminados:
- Naturaleza/valores/objetivos: TUE 1, 2, 3 → protocolo
- Cooperacion leal: TUE 4 → protocolo
- Atribucion/subsidiariedad/proporcionalidad: TUE 5 → protocolo
- Suspension de derechos: TUE 7 → protocolo
- Competencias UE (delimitacion/clasificacion): TFUE 2, 3, 4, 5, 6 → protocolo

Solo estan limpios TUE 49 (adhesion) y TUE 50 (retirada) = bloque "miembros".
Mapear unicamente 2 articulos sobre miembros daria una cobertura ~20% engaňosa
para el opositor (deja fuera valores, objetivos y competencias, el nucleo del tema).
Decision: dejar gen-13 en fallback honesto hasta resolver la reimportacion del TUE/TFUE.
