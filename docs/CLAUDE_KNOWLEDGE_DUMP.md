# GVAdictos Knowledge Dump For Claude

Leer este documento al iniciar cualquier sesion.

## Identidad

- Proyecto: GVAdictos.
- Objetivo: app local-first para estudiar A1-01 GVA 2025.
- Stack: Python, Streamlit, SQLite, pandas, pypdf.
- Regla juridica: no inventar; toda pregunta/explicacion juridica requiere fuente.

## Estado de datos

BD: `db/gvadicto.sqlite`.

Estado observado 2026-06-18:

- 81 leyes.
- 6792 articulos.
- 75 temas.
- 1286 enlaces `topic_sources`.
- 1079 enlaces con `article_id`.
- 16 temas con mapping fino.
- 20 preguntas.
- 0 intentos.
- 157 fuentes catalogadas.
- 32 findings de validacion.

## Carpetas clave

- `app.py`: UI Streamlit actual, monolitica.
- `src/core`: rutas, DB, exportaciones, fuentes.
- `src/laws`: parser/importador de leyes. Zona sensible.
- `src/tests`: CRUD preguntas.
- `src/mistakes`: intentos y fallos.
- `src/reports`: metricas dashboard.
- `src/studies`: anotaciones MVP actuales.
- `src/study`: backend futuro de estudio; no migrado real.
- `scripts`: herramientas de importacion, mapping, validacion, ops.
- `docs`: documentacion.
- `reports`: salidas generadas.
- `data/sources`: fuentes, manifiestos, convocatoria.
- `data/processed`: textos procesados.
- `db/backups`: backups.

## Tablas principales

- `laws`
- `articles`
- `topics`
- `topic_sources`
- `questions`
- `attempts`
- `study_annotations`
- `source_documents`
- `source_update_checks`
- `topic_validation_findings`

Tablas futuras StudyService:

- `study_article_notes`
- `study_highlights`
- `study_progress`
- `study_marks`
- `study_last_reviews`

## Que NO tocar sin permiso

- `db/gvadicto.sqlite`
- `articles`
- `topic_sources`
- `src/laws/importer.py`
- scripts `normalize_articles_*`
- scripts `apply_*` con escritura
- fuentes originales en `data/sources/leyes_originales`

## Scripts seguros

```powershell
python -m compileall app.py src scripts
python scripts/validate_article_quality.py
python scripts/report_mapping_status.py
python scripts/audit_fallback_topics.py
python scripts/audit_existing_fine_mappings.py
python scripts/app_healthcheck.py
python scripts/streamlit_diagnose.py
python scripts/report_study_features.py
python scripts/migrate_study_features.py --dry-run
python scripts/test_study_features.py
```

## Scripts peligrosos

No ejecutar sin permiso:

```powershell
python scripts/apply_mapping_review.py --apply
python scripts/apply_a1_article_validation.py
python scripts/apply_pilot_lpac_delimitation.py
python scripts/apply_fase2b_lrjsp_lcsp_delimitation.py
python scripts/apply_fase2e_pe13_delimitation.py --apply
python scripts/import_official_sources.py
python scripts/import_eurlex_direct.py
python scripts/import_topics_and_validate_coverage.py
python scripts/normalize_articles_inplace.py
python scripts/normalize_articles_pass2.py
python scripts/normalize_articles_pass3.py
python scripts/normalize_articles_pass4.py
```

## Mapping

- Fuente de verdad: `topic_sources`.
- Si `article_id` es NULL, no hay delimitacion fina.
- No inventar articulos.
- Revisar `reports/mapping_status.md`.
- Ultimo avance: PE-13 (`topic_id=28`) aplicado por Codex con `mapping_basis = validacion_articulos_claude_fase2e_pe13_2026_06_18`.
- PE-13 incluye Ley 40/2015 arts. 1-53 y 140-158, y Decreto 176/2014 arts. 1-21.
- Plantilla: `reports/mapping_review_template.csv`.
- Validar:

```powershell
python scripts/validate_mapping_review.py reports/mapping_review_template.csv
python scripts/apply_mapping_review.py reports/mapping_review_template.csv --dry-run
```

## StudyService

Codigo listo:

- `src/study/schema.py`
- `src/study/repository.py`
- `src/study/service.py`

No esta aplicado a BD real.

Antes de integrar UI:

```powershell
python scripts/migrate_study_features.py --dry-run
python scripts/test_study_features.py
```

Aplicar solo con permiso:

```powershell
python scripts/migrate_study_features.py --apply
```

Documento: `docs/STUDY_FEATURES_UI_INTEGRATION_PLAN.md`.

## UI

- `app.py` contiene toda la UI.
- Pestana Estudiar ya muestra temas y articulos delimitados.
- Si no hay mapping fino, muestra fallback.
- UI avanzada de notas/highlights/progreso pendiente.

## Operaciones

Streamlit:

```powershell
python scripts/streamlit_diagnose.py
streamlit run app.py
```

Tareas largas:

```powershell
python scripts/long_task_monitor.py -- <comando>
```

Healthcheck:

```powershell
python scripts/app_healthcheck.py
```

## Documentos a leer segun tarea

- Arquitectura: `docs/PROJECT_ARCHITECTURE.md`
- Handoff amplio: `docs/CLAUDE_CODE_HANDOFF.md`
- Deuda: `docs/TECHNICAL_DEBT.md`
- Roadmap: `docs/TECHNICAL_ROADMAP.md`
- Convenciones: `docs/DEVELOPMENT_CONVENTIONS.md`
- Diagramas: `docs/PROJECT_DIAGRAMS.md`
- Mapping: `docs/MAPPING_WORKFLOW.md`
- Study: `docs/STUDY_FEATURES_BACKEND.md`
- UI Study: `docs/STUDY_FEATURES_UI_INTEGRATION_PLAN.md`

## Prioridad recomendada

1. Cerrar calidad de datos/mappings juridicos en curso.
2. No tocar parser/importer mientras haya mappings activos.
3. Integrar StudyService con migracion autorizada.
4. Refactorizar UI por vertical slices.
5. Branding, tema, tipografia, assets y launcher.
