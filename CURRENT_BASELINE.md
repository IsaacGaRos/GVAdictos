# CURRENT_BASELINE — GVAdictos

**Fecha de corte:** 2026-06-21 · **Rama:** master · **Último commit relevante:** ver `git log`.
Este archivo describe el estado VERIFICADO. Si algo aquí no coincide con el código, gana el código (avísalo).

## Qué es
App local-first (Streamlit + SQLite) para preparar la oposición **A1-01 GVA 2025**.
Arranque: `launcher.bat` → opción 1 (`streamlit run app.py`). BD: `db/gvadicto.sqlite`.

## Estado funcional verificado (2026-06-21)
- `python -m compileall app.py src scripts` → **OK (exit 0)**.
- `import app` + funciones del ranking → **OK, sin excepciones**.
- Launcher: opción 1 (Streamlit), 2 (API), 3 (ambas), **4 (reconstruir ranking exámenes)**, 5 (salir).

## Ranking de exámenes oficiales (trabajo principal reciente — COMPLETO para A1-01)
- **Fuente: SOLO exámenes oficiales GVA** (cuestionario + plantilla de `sede.gva.es`). NUNCA simulacros de academia.
- **13 papers / 9 convocatorias A1-01 + C1-01 64/25**, **1185 preguntas**, **0 sin artículo** (invariante), **772 artículos** en ranking, **29 preguntas con >1 artículo**.
- A1-01 incorporadas: **1/25, 2/25(PI), 1/24, 1/23, 120/21** (texto) + **31/16, 32/16, 63/18, 64/18 V y H** (OCR).
- Falta solo **A1-01 22/15** (no publicado online).
- UI: pestaña **"🔥 Mas preguntado"** (tabs[12]) — orden por *veces* o por *materia (ley→artículos)*, filtro por cuerpo, slider top 100, y estudio del artículo (texto + preguntas que lo citan). También expander dentro de **Estudiar**.
- Niveles de vínculo (todos `requiere_revision_humana`): `articulo_explicito` (0.85–0.95) · `articulo_inferido` (0.30–0.60) · `articulo_inferido_global` (0.10–0.25). OCR lleva `notes='ocr'`, confianza ≤0.7.

## Pipeline del ranking (reproducible)
`python scripts/run_exam_pipeline.py` (o launcher opción 4). Orden:
1. `rebuild_official_exams.py` — exámenes en TEXTO (catálogo `OFFICIAL[]`).
2. `ocr_exam_loader.py` — exámenes ESCANEADOS (catálogo `OCR_EXAMS[]`); OCR vía `ocr_extract.py` (PyMuPDF + RapidOCR, sin admin).
3. `enrich_multiarticle.py` — preguntas con >1 artículo citado (una sola ley).
4. `infer_and_link.py` — infiere artículo dentro de la ley citada.
5. `infer_global_fallback.py` — barrida global: toda pregunta → ≥1 artículo. Reconstruye `article_exam_frequency`.

## Tablas BD relevantes
`exam_papers` (fuente_tipo='oficial_gva', parte, notes), `exam_questions` (numero, enunciado, respuesta_oficial, anulada), `exam_question_options`, `exam_question_links` (law_id, article_id, tipo_relacion, confianza, validation_status), `article_exam_frequency` (article_id, total_count, explicit_count, inferred_count, exam_sources).

## Resto del proyecto (preexistente, estable)
- 12.838 artículos / ~82 leyes / 75 temas A1 importados; normativa oficial trazada (BOE/DOGV/EUR-Lex).
- Pestaña **Estudiar**: temas A1, normativa por tema, anotaciones, Pomodoro, plan de estudio diario, recursos CEF.
- TTS, Modo test, Modo examen/simulacros, Fallos, Informes/CSV, Cuentas.
- 20 preguntas piloto Ley 39/2015 (todas `requiere_revision=1`) — NO son banco definitivo.

## Doc de referencia clave
`docs/EXAM_RANKING_PIPELINE.md` (pipeline exámenes), `docs/CLAUDE_HANDOFF.md`, `CLAUDE.md` (reglas), `docs/ROADMAP.md`.
