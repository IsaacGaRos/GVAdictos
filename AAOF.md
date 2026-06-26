# AAOF.md — GVAdictos

> Capa compacta de orquestación (AAOF). Léela **antes** que el código.
> Marco global: `~/.claude/CLAUDE.md` + skill `aaof`. Corta y enlazada; no duplica el código ni git.

## Qué es
App de estudio para oposición TAG-GVA. **Streamlit + SQLite** (`app.py`, `streamlit run app.py` o `launcher.bat`).
Repo: https://github.com/IsaacGaRos/GVAdictos (master, público). Local: `C:\Users\isaac\Desktop\GVAdictos`.

## Mapa rápido (índice, no el árbol)
- `app.py` — UI Streamlit, ~13 pestañas. Pestaña 7 "Estudiar" y tabs[12] "🔥 Mas preguntado".
- `src/core/paths.py` — apunta a la BD correcta (**`db/gvadicto.sqlite`**, sin 's').
- `src/api/` (FastAPI), `src/db/models.py` (SQLAlchemy+Alembic), `src/billing/` (Stripe), `src/sync/` (Drive).
- `scripts/` — pipelines de datos. Clave: `scripts/run_exam_pipeline.py` (5 pasos, ranking oficial).
- `docs/EXAM_RANKING_PIPELINE.md`, `NEXT_CHAT_START_HERE.md` (roadmap), `RULES_DO_NOT_BREAK.md`.
- Detalle vivo en memoria: [[project_complete_state]], [[streamlit_architecture_gotchas]], [[exam_ranking_official_only]].

## Cómo verificar "hecho" aquí
- `python validate_article_quality.py` debe quedar en **PASS** tras tocar datos.
- Cambios de UI: arrancar `streamlit run app.py` y/o test con Streamlit `AppTest` → **0 excepciones** (no basta `compileall`).
- Invariante de datos: **0 preguntas sin artículo** en el ranking oficial.

## Defaults de orquestación
- Preguntas/UI menor/copys → Haiku, contexto mínimo (grep en `app.py`).
- Feature normal de UI o script → Sonnet, medio; leer solo la pestaña/función afectada.
- Pipeline de datos jurídicos / esquema BD / migraciones Alembic → Opus + alto razonamiento; **alto riesgo**.
- **Zonas de alto riesgo (revisar con modelo fuerte):** cualquier escritura masiva en BD, `data/sources/leyes_originales/`, pipeline de ranking, contenido jurídico.
- **Zonas baratas (delegar a Haiku):** copys de UI, estilos, expanders, tests triviales.

## Reglas de datos críticas (RULES_DO_NOT_BREAK)
- No inventar contenido jurídico; todo con fuente. Preguntas IA → `requiere_revision=1`.
- No modificar `data/sources/leyes_originales/`. Backup antes de escritura masiva.
- IDs protegidos: Código Civil stub (art.2, id=104991); topic_sources {67,69,70}.
- BD real = `db/gvadicto.sqlite`. `db/gvadictos.sqlite` (con 's') = Alembic, vacía. No confundir.

## Trampas conocidas (Streamlit/SQLite)
- DictRow; **no cachear conexiones**; `commit` en mutaciones de estudio; TTS por iframes con gesto de usuario.
- Artículos: usar `st.markdown` con `white-space:pre-wrap`, no `st.text_area` (corta a 400px).
