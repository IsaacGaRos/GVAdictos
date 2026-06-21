# MEMORY_COMPACT_DUMP — GVAdictos

Volcado denso para reanudar sin contexto previo. Léelo junto a `CURRENT_BASELINE.md` y `RULES_DO_NOT_BREAK.md`.

## Usuario / trabajo
- Opositor A1-01 GVA. Estudia con **Academia Auténtica** (≈75% de plazas la pasada convocatoria → sus indicaciones priorizan, no son autoridad jurídica).
- Responder SIEMPRE en español. Trabaja con autonomía cuando dice "procede"/"adelante".
- Repo: `https://github.com/IsaacGaRos/GVAdictos` (público, master). Windows; shell PowerShell + Bash. Python 3.10 en `app.py`/scripts.

## Cómo arranca / valida
- App: `launcher.bat` → 1, o `python -m streamlit run app.py` (localhost:8501).
- Reconstruir ranking exámenes: `launcher.bat` → 4, o `python scripts/run_exam_pipeline.py`.
- Validar: `python -m compileall app.py src scripts`.

## Lo hecho en las últimas sesiones (exámenes oficiales → ranking)
- Se detectó que el ranking previo estaba CONTAMINADO con simulacros de academia y matching por keywords; se REHIZO desde cero solo con oficiales.
- Descarga de plantillas oficiales desde `sede.gva.es`: la etapa **"Plantilla de respuestas del 1.er ejercicio"**; `id_etapa` = posición cronológica de la etapa (Bases=1). PDFs en `sede.gva.es/descarregues/AAAA/MM/NNNNNN-...pdf`.
- id_emp A1-01: 1/25=103841(et.9), 2/25=103842(et.9), 1/24=98131(et.14), 1/23=92921(et.10), 120/21=86906(et.12). 64/25 C1=104155(et.9). 22/15=64569 (sin cuestionario online).
- Parser texto `parse_official_exam.py`: formatos `1.`, `1.-`, `3.- `. Bilingüe (castellano primero); para por nº esperado.
- Pre-2021 A1 escaneados → OCR (PyMuPDF render 300dpi + RapidOCR ONNX, sin admin). `ocr_extract.py` (acepta rango de páginas). Loader `ocr_exam_loader.py`: respuestas de plantilla en texto/.txt + segmentación por nº (no secuencial; bloque más largo por nº; separador `[.)\-]+`). Calidad: 63/18 113/120, 64/18V 70/72, 64/18H 71/72, 31/16 71/120, 32/16 57/120 (escaneo 2016 peor).
- Combinado 63-64_18 (231 págs): pp1-3 plantillas (texto), resto escaneado. Mapa: 63 cast pp4-46, 63 val pp47-~95, 64V cast ~p106-137, 64V val ~p138-167, **64H cast pp169-196**, 64H val pp196-231. Plantillas → `.txt`; PDF de 13MB se borra tras OCR.
- Multi-artículo `enrich_multiarticle.py`: si la pregunta cita UNA ley, vincula TODOS los artículos citados (sueltos+rangos). 29 preguntas con >1 art.
- Inferencia: `infer_and_link.py` (dentro de la ley) + `infer_global_fallback.py` (índice invertido sobre 6794 arts; garantiza ≥1 art/pregunta).

## Cifras actuales (2026-06-21)
13 papers (9 conv. A1-01 + C1-01 64/25) · 1185 preguntas oficiales · 0 sin artículo · 772 artículos en ranking · 29 con >1 artículo.

## Gotchas Streamlit/SQLite (no repetir errores)
- `connect()` → `DictRow` (soporta `r["col"]` y `r[0]`). No cachear conexiones; `commit` en mutaciones.
- Terminal Windows muestra `�` en acentos pero el dato es UTF-8 correcto (no es corrupción). Validar con `Read`/UTF-8, no por el terminal.
- `pdfplumber` cuenta U+FFFD reales; si =0, el texto está limpio.
- Insertar una pestaña nueva en mitad de `TABS` re-numera `tabs[i]` → añadir al FINAL (la de ranking es `tabs[12]`).

## Pendientes inmediatos (no bloqueantes)
- A1-01 22/15 no disponible online (cerrado, documentado).
- 2ª parte teórico-práctica de C1-01 64/25 no localizada; otros cuerpos (A2-01, C2-01) sin cargar.
- Artículos inferidos (≈) y preguntas OCR: pendientes de revisión humana.
- Mañana (2026-06-22) el usuario envía la planificación mensual de Auténtica → alinear desarrollo a ella.
