# Fase 2B — Delimitación fina LRJSP (Ley 40/2015) y LCSP (Ley 9/2017)

**Autor**: Claude Code
**Fecha**: 2026-06-18
**Nivel de rigor**: extremadamente alto
**mapping_basis**: `delimitacion_convocatoria_titulos_claudecode_2026_06_18` (mismo método que Fase 2A LPAC)
**Estado**: validado contra fuente oficial, pendiente de revisión humana

## Alcance aplicado (3 temas de alta confianza)

| Tema | id | Norma | Estructura | Artículos | Nº |
|---|---|---|---|---|---|
| PE-14 | 29 | Ley 40/2015 (law 4) | Título I + Título II | 54–139 | 92 |
| PE-22 | 37 | Ley 9/2017 LCSP (law 13) | Libro Segundo | 115–315 | 201 |
| PE-23 | 38 | Ley 9/2017 LCSP (law 13) | Libro Tercero + Cuarto | 316–346 | 31 |

Ninguno se solapa con los 8 mapeos de Codex ni con el piloto LPAC (24–27).

## Estructura verificada en BD

**Ley 40/2015 (165 arts, incluye bis 46b/55b/84b/108b/q/s/t)**:
- Título Preliminar (1–53): disposiciones generales, órganos, sancionadora, responsabilidad, electrónico, convenios
- **Título I (54–80)**: Administración General del Estado
- **Título II (81–139)**: organización y funcionamiento del sector público institucional
- Título III (140–158): relaciones interadministrativas

→ **PE-14** = Título I + Título II (54–139), verbatim del enunciado oficial "Administración General del Estado. Organización y funcionamiento del sector público institucional".

**Ley 9/2017 LCSP (346 arts, refs enteros)**:
- Título Preliminar + Libro I (1–114) → PE-21 (Codex)
- **Libro Segundo (115–315)**: "De los contratos de las Administraciones Públicas"
- **Libro Tercero (316–322)**: "De los contratos de otros entes del sector público"
- **Libro Cuarto (323–346)**: "Organización administrativa para la gestión de la contratación"

→ **PE-22** = Libro Segundo (115–315). **PE-23** = Libro Tercero + Cuarto (316–346), contiguos.

Partición completa de LCSP: PE-21 (1–114) + PE-22 (115–315) + PE-23 (316–346) = 346.

## Nota técnica: selección por rango directo (no `best_articles_in_range`)

Se seleccionaron los artículos por `CAST(article_ref AS INTEGER) BETWEEN inicio AND fin`
(refs únicos en la BD normalizada, sin duplicados). **No se usó** el helper
`best_articles_in_range` de Codex porque su filtro `is_probable_article` exige que el
`title` de los artículos *bis* empiece por "is." (artefacto del parser antiguo); en la BD
normalizada esos artículos llevan su epígrafe real, por lo que el helper los **descartaría**
(46b, 55b, 84b, 108b/q/s/t). La selección por rango los incluye correctamente por su número base.

## Confianza

**ALTA** en los 3 temas: norma única (salvo Decreto en PE-13, diferido), delimitación =
nombre verbatim del título/libro en el enunciado oficial de la convocatoria, límites
verificados artículo a artículo contra epígrafes BOE, rangos contiguos, conteos exactos,
contaminación descartada por spot-check.

## ⚠️ PE-13 DIFERIDO — contaminación de datos en Ley 40/2015 (law_id=4)

PE-13 (Título Preliminar 1–53 + Título III 140–158 + Decreto 176/2014) **no se aplica**.

Motivo: en `law_id=4`, los **artículos 24–27 contienen el texto de la Ley 50/1997 del Gobierno**
(Título V), no de la Ley 40/2015:
- art 24 → "De la forma y jerarquía de las disposiciones... del Gobierno de la Nación" (L50/1997 art 24)
- art 25 → "Plan Anual Normativo" (L50/1997 art 25)
- art 26 → "Procedimiento de elaboración de normas con rango de Ley y reglamentos" (L50/1997 art 26)
- art 27 → "Tramitación urgente de iniciativas normativas en el ámbito de la AGE" (L50/1997 art 27)

Los arts. 24–27 **reales** de la Ley 40/2015 (Recusación, Principio de legalidad, Irretroactividad,
Tipicidad) **faltan** en la BD. La contaminación está **aislada en 24–27**; el resto (1–23, 28–158)
es correcto, por eso PE-14 (54–139) es seguro.

**Acción requerida (fuera de mi alcance: no toco `articles` ni reimporto)**: corregir la importación
de `law_id=4` (recuperar arts 24–27 reales de Ley 40/2015). Es trabajo de import → corresponde a Codex.
Una vez corregido, PE-13 es delimitable como T.Preliminar (1–53) + T.III (140–158) + Decreto 176/2014 (1–21).

## Reversibilidad

- Backup previo automático: `db/gvadicto.backup_prepilot_<timestamp>.sqlite`.
- Rollback selectivo de TODO el mapping Claude Code (2A+2B):
  `DELETE FROM topic_sources WHERE mapping_basis = 'delimitacion_convocatoria_titulos_claudecode_2026_06_18';`
- Script idempotente: `scripts/apply_fase2b_lrjsp_lcsp_delimitation.py` (borra solo sus topics 29/37/38).
