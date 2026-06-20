# Ranking de exámenes oficiales — Pipeline (CORREGIDO)

**Fecha:** 2026-06-20
**Estado:** Operativo, solo fuentes oficiales

## Corrección importante (feedback del usuario)

La primera versión del ranking estaba **contaminada con simulacros de academia**
(TSGV / EraCEF) y matching por keywords, y no contenía ni una pregunta oficial de
A1-01. Se rehízo por completo:

- **Solo exámenes OFICIALES GVA** (cuestionario + plantilla de respuestas
  publicados en `sede.gva.es`). Los simulacros de academia NO entran en el ranking.
- `exam_papers.fuente_tipo = 'oficial_gva'` marca el origen; cualquier import de
  simulacro debe usar otro valor y queda excluido de las consultas del ranking.

## Fuentes oficiales: cómo se localizan y descargan

Las plantillas oficiales contienen **cuestionario completo + plantilla de
respuestas** en un solo PDF (o dos, una por parte del 1er ejercicio).

1. Ficha de la convocatoria: `sede.gva.es/es/inicio/.../detalle_oposiciones?id_emp=XXXX`
2. Etapa **"Plantilla de respuestas del 1.er ejercicio"** → página de la etapa
   `sede.gva.es/es/detall-ocupacio-publica?id_emp=XXXX&id_etapa=N`
3. El PDF está en `sede.gva.es/descarregues/AAAA/MM/NNNNNN-Plantilla_de_respuestas_y_cuestionarios*.pdf`

`id_emp` conocidos: A1-01 1/25 = 103841 (etapa 9), C1-01 64/25 = 104155 (etapa 9),
A1-01 1/24 = 98131, A2-01 34/25 = 104139, C1-01 12/23 = 93056.

> Nota: el `id_etapa` no es estable entre convocatorias; conviene enumerar el
> "Listado de etapas" y localizar la de plantilla.

## Pipeline (scripts canónicos)

```powershell
# 1. Parsea las plantillas oficiales del catálogo OFFICIAL[] y reconstruye
#    exam_questions + exam_question_options + exam_question_links (ley/art explícito)
python scripts/rebuild_official_exams.py

# 2. Infiere el artículo de las preguntas que citan ley pero no artículo,
#    comparando el texto de la respuesta correcta con el articulado de esa ley.
#    (confianza baja, validation_status='requiere_revision_humana')
python scripts/infer_and_link.py
```

Módulos de apoyo:
- `scripts/parse_official_exam.py` — parser robusto (plantilla + preguntas + opciones).
- `scripts/exam_linker.py` — cita→ley (núm/año y nombres especiales) y artículo explícito.

Para añadir una convocatoria nueva: descargar el/los PDF a
`data/examenes_oficiales/<CUERPO>/<AÑO>/`, añadir la entrada a `OFFICIAL[]` en
`rebuild_official_exams.py` y reejecutar los 2 pasos.

## Vinculación: niveles de confianza

| tipo_relacion        | criterio                                              | confianza | estado |
|----------------------|-------------------------------------------------------|-----------|--------|
| `articulo_explicito` | la pregunta/respuesta cita "artículo N" + ley en BD   | 0.8–0.95  | pendiente_revision_humana |
| `ley_explicita`      | cita la ley pero no el artículo (o art. no en BD)     | 0.8–0.95  | pendiente_revision_humana |
| `articulo_inferido`  | deducido del texto de la respuesta correcta (TF-IDF)  | 0.30–0.60 | requiere_revision_humana |

Cumple CLAUDE.md: nada jurídico se da por validado; todo queda marcado para
revisión humana. El ranking distingue **✓ explícito** de **≈ inferido**.

## Estado actual

- Exámenes oficiales procesados: **2** (A1-01 1/25 — 2 partes; C1-01 64/25).
- Preguntas: **310** (220 con ley identificada, 64 con artículo explícito).
- Artículos en ranking: **195** (66 con ≥1 cita explícita).
- Top leyes (ambos cuerpos): Constitución 28, Ley 1/2015 25, Ley 39/2015 25,
  LCSP 20, Ley 4/2021 18, Ley 5/1983 12, Ley 40/2015 12.

## UI (pestaña Estudiar → "🔥 Lo más preguntado en exámenes oficiales GVA")

- Filtro por **cuerpo/oposición** (A1-01, C1-01, …).
- Pestaña **Artículos** (marca ✓/≈, conteos explícito/inferido/total).
- Pestaña **Leyes** (cobertura alta y fiable).
- **Estudiar artículo desde el ranking**: muestra el texto del artículo y las
  preguntas oficiales que lo citan (con su respuesta oficial).

## Pendiente (enriquecimiento futuro)

- Más convocatorias: A1-01 1/24, A2-01 34/25, C1-01 27/24, C2-01… (descargar
  plantilla oficial vía el método de arriba y añadir a `OFFICIAL[]`).
- 2ª parte (teórico-práctica) de C1: pendiente de localizar su plantilla.
- Revisión humana de los artículos inferidos (≈) y de las leyes sectoriales no
  importadas (Ley 13/2010, 15/2018, Decreto Legislativo 1/2021, …).
