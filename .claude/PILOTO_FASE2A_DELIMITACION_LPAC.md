# Piloto Fase 2A — Delimitación fina LPAC (Ley 39/2015)

**Autor**: Claude Code
**Fecha**: 2026-06-18
**Nivel de rigor**: extremadamente alto
**mapping_basis**: `delimitacion_convocatoria_titulos_claudecode_2026_06_18`
**Estado**: validado contra fuente oficial, pendiente de revisión humana

## Alcance

Delimitación fina de **4 temas en fallback** de la Parte específica, todos sobre
la **Ley 39/2015 (LPACAP)**, partiendo el articulado de la ley por sus títulos.
Estos 4 temas NO están entre los 8 ya validados por Codex y no se solapan con ellos.

## Fuente de delimitación (prioridad)

1. **Convocatoria oficial A1-01 2025** (bases DOGV, `data/sources/convocatorias/A1-01_2025/`).
   El enunciado oficial de cada tema describe funcionalmente bloques que se
   corresponden 1:1 con los títulos de la Ley 39/2015. Esta es la fuente de
   mayor autoridad (es el propio temario oficial), por encima de Auténtica.
2. **Estructura oficial BOE-A-2015-10565** (texto consolidado en BD, 133 artículos),
   usada para fijar los límites exactos de cada título.
3. **Auténtica** (`autentica_auxiliary_normative_indications.md`, PE-06) como
   contraste: confirma que el Título VI (arts. 127-133) pertenece al Tema 6 PE
   (iniciativa legislativa y potestad reglamentaria), por lo que queda **fuera**
   de estos 4 temas. Coherente con la partición propuesta.

## Estructura verificada de la Ley 39/2015 en BD

| Título | Contenido | Artículos |
|---|---|---|
| Preliminar | Disposiciones generales (objeto, ámbito) | 1–2 |
| I | De los interesados en el procedimiento | 3–12 |
| II | De la actividad de las AAPP (registros, archivo, términos y plazos) | 13–33 |
| III | De los actos administrativos (requisitos, eficacia, notificación, nulidad/anulabilidad) | 34–52 |
| IV | Del procedimiento administrativo común (iniciación, ordenación, instrucción, finalización, ejecución, tramitación simplificada) | 53–105 |
| V | De la revisión de los actos en vía administrativa (revisión de oficio, recursos) | 106–126 |
| VI | De la iniciativa legislativa y potestad reglamentaria | 127–133 → Tema 6 PE |

## Mapping propuesto

| Tema | id | Enunciado (resumen) | Título(s) | Artículos | Nº arts |
|---|---|---|---|---|---|
| PE-09 | 24 | objeto/ámbito + interesados + actividad AAPP + términos/plazos + identif./firma/registro/archivo | Preliminar + I + II | 1–33 | 33 |
| PE-10 | 25 | actos administrativos: requisitos, eficacia, nulidad/anulabilidad, notificación | III | 34–52 | 19 |
| PE-11 | 26 | garantías + iniciación/ordenación/instrucción/finalización/ejecución + tramitación simplificada | IV | 53–105 | 53 |
| PE-12 | 27 | revisión de oficio + recursos administrativos | V | 106–126 | 21 |

Partición completa de Títulos Preliminar–V (126 arts), sin solapes ni huecos.
Título VI (127–133) reservado al Tema 6 PE (fuera de este piloto).

## Confianza

**ALTA** para los 4 temas:
- Norma única (Ley 39/2015), ya en BD, texto consolidado limpio (QA superado).
- Delimitación derivada del enunciado oficial de la convocatoria (no de rangos genéricos inventados).
- Límites de título verificados artículo a artículo contra la estructura BOE.
- Rangos contiguos, conteos exactos, sin refs ausentes.

## Notas / ambigüedad

- Ninguna ambigüedad de límites de título.
- Los temas conservan sus filas `topic_sources` previas con `article_id IS NULL`
  (provenance `explicit_coverage_csv` / `inferencia_texto_temario_pendiente_validacion`).
  Son inofensivas: la UI prioriza el mapping fino por norma. No se borran para no
  perder trazas previas ni pisar trabajo de Codex.

## Reversibilidad

- Backup previo automático: `db/gvadicto.backup_prepilot_<timestamp>.sqlite`.
- Rollback selectivo:
  `DELETE FROM topic_sources WHERE mapping_basis = 'delimitacion_convocatoria_titulos_claudecode_2026_06_18';`
- Script idempotente: `scripts/apply_pilot_lpac_delimitation.py`.
