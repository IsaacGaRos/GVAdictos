# Development Conventions

Guia definitiva para continuar GVAdictos.

## Principios

- Cambios pequenos y verificables.
- No inventar contenido juridico.
- Toda pregunta/explicacion juridica debe tener fuente.
- No modificar `articles`, `topic_sources`, parser/importer o BD sin tarea explicita.
- No ejecutar scripts con escritura sin backup y dry-run previo.
- No tocar originales en `data/sources/leyes_originales`.

## Commits

Formato recomendado:

```text
area: resumen breve
```

Areas sugeridas:

- `docs`
- `ui`
- `study`
- `mapping`
- `import`
- `tests`
- `ops`
- `data`

Ejemplos:

```text
docs: consolidate Claude handoff
study: add article progress backend
ops: add Streamlit healthcheck
```

## Nombres

- Nombre visible: `GVAdictos`.
- Foco actual: A1-01 GVA 2025.
- Mantener nombres internos si cambiarlos puede romper imports.
- Evitar nuevos archivos con `GVAdicto` singular.

## Scripts

Antes de ejecutar un script, clasificar:

- Read-only: seguro.
- Dry-run: seguro si no cambia hash BD.
- Apply/import/normalize: requiere permiso explicito.

Scripts normalmente seguros:

```powershell
python scripts/validate_article_quality.py
python scripts/report_mapping_status.py
python scripts/audit_fallback_topics.py
python scripts/audit_existing_fine_mappings.py
python scripts/validate_mapping_review.py reports/mapping_review_template.csv
python scripts/app_healthcheck.py
python scripts/streamlit_diagnose.py
python scripts/report_study_features.py
```

Scripts peligrosos o sensibles:

```powershell
python scripts/import_official_sources.py
python scripts/import_eurlex_direct.py
python scripts/import_topics_and_validate_coverage.py
python scripts/normalize_articles_inplace.py
python scripts/normalize_articles_pass2.py
python scripts/normalize_articles_pass3.py
python scripts/normalize_articles_pass4.py
python scripts/apply_mapping_review.py --apply
python scripts/apply_a1_article_validation.py
python scripts/apply_pilot_lpac_delimitation.py
python scripts/apply_fase2b_lrjsp_lcsp_delimitation.py
```

## Validaciones

Validacion base:

```powershell
python -m compileall app.py src scripts
python scripts/validate_article_quality.py
python scripts/report_mapping_status.py
python scripts/app_healthcheck.py
```

Backend estudio:

```powershell
python scripts/migrate_study_features.py --dry-run
python scripts/test_study_features.py
python scripts/report_study_features.py
```

Streamlit:

```powershell
python scripts/streamlit_diagnose.py
streamlit run app.py
```

## Backups

Antes de cualquier escritura sobre BD:

1. Tomar hash:

```powershell
Get-FileHash -Algorithm SHA256 db/gvadicto.sqlite
```

2. Crear backup:

```powershell
python scripts/backup.py
```

3. Ejecutar dry-run si existe.

4. Validar despues.

## Migraciones

- Dry-run por defecto.
- `--apply` solo con autorizacion expresa.
- Backup automatico antes de aplicar.
- No introducir migracion que borre datos.
- Si se acumulan migraciones, crear tabla `schema_migrations`.

## Flujo recomendado

1. Leer `docs/CLAUDE_KNOWLEDGE_DUMP.md`.
2. Leer documento especifico de la tarea.
3. Tomar hash BD si la tarea toca datos.
4. Ejecutar solo scripts seguros.
5. Hacer cambio pequeno.
6. Compilar.
7. Ejecutar validaciones relacionadas.
8. Reportar archivos, comandos, riesgos y siguiente paso.

## Rollback

- Codigo: revertir solo cambios propios.
- BD: restaurar backup desde `db/backups`.
- Reports: regenerar si son derivados.
- No reescribir fuentes originales.

