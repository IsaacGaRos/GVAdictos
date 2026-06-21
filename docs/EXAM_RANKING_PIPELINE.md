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

**Método del `id_etapa`** (verificado): `id_etapa` = posición cronológica de la
etapa contando "Bases y apertura de plazo" = 1. Enumerar el "Listado de etapas" en
orden cronológico, localizar "Plantilla de respuestas del 1.er ejercicio" y usar su
número de posición como `id_etapa`. Al abrir esa etapa, las URLs de los PDF aparecen
como `sede.gva.es/descarregues/...`.

`id_emp` / `id_etapa` (plantilla) verificados para A1-01:

| Convocatoria | id_emp  | id_etapa | PDFs |
|--------------|---------|----------|------|
| 1/25 (TL)    | 103841  | 9        | 1ª parte + 2ª parte |
| 2/25 (PI)    | 103842  | 9        | 1 PDF (40 preg.) |
| 1/24 (TL)    | 98131   | 14       | MAÑANA (1ª, 160) + TARDE (2ª, 40) |
| 1/23 (TL)    | 92921   | 10       | 1 PDF (1ª y 2ª parte) |
| 120/21 (TL)  | 86906   | 12       | 1 PDF (120 preg.) |

Otros: C1-01 64/25 = 104155 (etapa 9), A2-01 34/25 = 104139, C1-01 12/23 = 93056.

> El parser acepta los formatos de enunciado `1. `, `1.-` y `3.- ` (2021-2025).
> Algunos PDF antiguos (p.ej. `plantilla_3-4_22.pdf`) son SOLO plantilla de
> respuestas sin cuestionario: no permiten extraer preguntas.

## Pipeline (scripts canónicos)

Orquestador (también accesible desde `launcher.bat` opción 4):

```powershell
python scripts/run_exam_pipeline.py
```

Ejecuta en orden:

```powershell
# 1. Exámenes en TEXTO (catálogo OFFICIAL[]): parseo + ley/art explícito
python scripts/rebuild_official_exams.py
# 2. Exámenes ESCANEADOS (catálogo OCR_EXAMS[]): OCR + ley/art
python scripts/ocr_exam_loader.py
# 3. Inferencia de artículo por ley (respuesta correcta vs articulado de esa ley)
python scripts/infer_and_link.py
# 4. Barrida global: toda pregunta sin artículo -> inferencia contra TODO el
#    articulado (garantiza >=1 artículo por pregunta)
python scripts/infer_global_fallback.py
```

Módulos de apoyo:
- `scripts/parse_official_exam.py` — parser de plantillas en texto (formatos `1.`, `1.-`, `3.- `).
- `scripts/exam_linker.py` — cita→ley (núm/año y nombres especiales) y artículo explícito.
- `scripts/ocr_extract.py` — OCR de PDF escaneado (PyMuPDF render + RapidOCR) → `.txt` cache.

Para añadir una convocatoria: descargar el/los PDF a
`data/examenes_oficiales/<CUERPO>/<AÑO>/`, añadir la entrada a `OFFICIAL[]`
(texto) o `OCR_EXAMS[]` (escaneado) y reejecutar el orquestador.

## Vinculación: niveles de confianza

| tipo_relacion              | criterio                                                  | confianza | estado |
|----------------------------|-----------------------------------------------------------|-----------|--------|
| `articulo_explicito`       | la pregunta/respuesta cita "artículo N" + ley en BD       | 0.8–0.95  | pendiente_revision_humana |
| `ley_explicita`            | cita la ley pero no el artículo (o art. no en BD)         | 0.8–0.95  | pendiente_revision_humana |
| `articulo_inferido`        | deducido del texto de la respuesta correcta vs su ley     | 0.30–0.60 | requiere_revision_humana |
| `articulo_inferido_global` | barrida global contra TODO el articulado (sin ley previa) | 0.10–0.25 | requiere_revision_humana |

Cumple CLAUDE.md: nada jurídico se da por validado; todo queda marcado para
revisión humana. El ranking distingue **✓ explícito** de **≈ inferido**.
**Invariante garantizado: toda pregunta oficial tiene ≥1 artículo vinculado.**

Las preguntas de exámenes OCR llevan además `notes='ocr'` en su `exam_paper` y
confianza recortada (≤0.7), por la menor fidelidad de la extracción.

## Estado actual

- Exámenes oficiales procesados: **8** en 2 cuerpos.
  - A1-01 (texto): 1/25 (2 partes), 2/25 (PI), 1/24 (2 partes), 1/23, 120/21.
  - A1-01 (OCR, escaneados 2016): 31/16, 32/16.
  - C1-01: 64/25.
- Preguntas: **930** (modernas 803 + OCR 2016 ~127).
- **Invariante: 0 preguntas sin artículo** (665 artículos en el ranking).
- Top leyes A1-01: Constitución 87, Ley 39/2015 82, Ley 4/2021 59, Ley 1/2015 56,
  Ley 40/2015 51, Ley 5/1983 49, LCSP 44, TFUE 43.
- UI: ranking ajustable hasta **top 100** (slider), filtro por cuerpo.

## UI (pestaña Estudiar → "🔥 Lo más preguntado en exámenes oficiales GVA")

- Filtro por **cuerpo/oposición** (A1-01, C1-01, …).
- Pestaña **Artículos** (marca ✓/≈, conteos explícito/inferido/total).
- Pestaña **Leyes** (cobertura alta y fiable).
- **Estudiar artículo desde el ranking**: muestra el texto del artículo y las
  preguntas oficiales que lo citan (con su respuesta oficial).

## Pendiente (enriquecimiento futuro)

- **A1-01 63/18 y 64/18 (2018)**: el PDF oficial mezcla varias plantillas (texto)
  con cuestionarios escaneados en 231 páginas. Requiere OCR dirigido a las páginas
  del cuestionario de cada turno; pendiente por coste/segmentación.
- **A1-01 22/15 (2015)**: no localizada online.
- OCR 2016: se recuperan ~70/120 (31/16) y ~57/120 (32/16) preguntas; el resto se
  pierde por el desorden de columnas del OCR. Mejorable con mejor reconstrucción.
- Otros cuerpos: A2-01 34/25, C1-01 27/24/65/25, C2-01.
- Revisión humana de los artículos inferidos (≈) — especialmente los
  `articulo_inferido_global` (confianza ≤0.25) y las preguntas OCR.
