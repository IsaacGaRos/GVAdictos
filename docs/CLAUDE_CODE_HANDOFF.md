# Claude Code Handoff

Documento operativo para continuar GVAdictos sin redescubrir arquitectura.

## Estado actual

GVAdictos es una app local-first para estudiar A1-01 GVA 2025.

Estado read-only observado el 2026-06-18:

- 81 normas en `laws`.
- 6792 articulos en `articles`.
- 75 temas en `topics`.
- 1192 filas en `topic_sources`.
- 985 filas `topic_sources` con `article_id`.
- 15 temas con mapping fino.
- 20 preguntas.
- 0 intentos.
- 0 anotaciones MVP.
- 157 fuentes catalogadas.
- 206 checks de fuentes.
- 32 findings de validacion de temas.

Hash BD al consolidar:

```text
59B6DBFA3430C33ACF944CBE658397B8265FEF595F5A1A27BCCA8BF5DED8FF02
```

## Que ya funciona

- Streamlit arranca desde `app.py`.
- Importacion basica de TXT/MD.
- Catalogo de fuentes.
- Tabla de leyes/articulos.
- CRUD de preguntas.
- Modo test basico.
- Registro de intentos/fallos.
- Informes y exportacion CSV/Anki basica.
- Estudio por tema con separacion general/especial.
- Fallback explicito cuando no hay delimitacion fina.
- Anotaciones MVP en `study_annotations`.
- Auditorias de mapping.
- Plantilla de revision de mapping.
- Validacion de plantilla sin escritura.
- Healthcheck.
- Diagnostico Streamlit.
- Monitor de tareas largas.
- Backend `src/study` preparado en codigo, pendiente de migracion real.

## Que no funciona o no esta integrado

- StudyService moderno no esta integrado en `app.py`.
- Tablas `study_article_notes`, `study_highlights`, `study_progress`, `study_marks`, `study_last_reviews` no estan aplicadas a la BD real.
- UI visual pulida no esta implementada.
- Branding completo no esta cerrado.
- Launcher Windows final no esta implementado.
- Tema claro/oscuro, tipografia y assets no estan integrados.
- Remapeo robusto de anotaciones tras cambios normativos no existe.
- Generacion avanzada de preguntas juridicas debe esperar a fuente validada.

## Que NO debe romperse

- `articles`: no tocar salvo tarea explicita de importacion/normalizacion.
- `topic_sources`: no tocar salvo tarea explicita de mapping.
- `src/laws/importer.py`: no tocar sin pruebas especificas.
- Scripts de normalizacion: no ejecutar sin backup y permiso.
- Fuentes originales en `data/sources/leyes_originales`: no modificar.
- Mappings validados con `mapping_basis` protegido.
- `study_annotations` legacy mientras `app.py` lo use.

## Modulos estables

- `src/core/paths.py`
- `src/core/db.py` para conexion basica.
- `src/core/export.py`
- `src/core/source_catalog.py`
- `src/tests/repository.py`
- `src/mistakes/repository.py`
- `src/reports/basic.py`
- Scripts de auditoria read-only.
- Scripts de healthcheck/diagnostico.

## Modulos experimentales

- `src/study/*`: backend futuro, probado con SQLite temporal, no migrado real.
- `src/studies/annotations.py`: MVP actual; puede ser legacy.
- `app.py`: funcional pero monolitico y fragil para refactors grandes.
- Scripts `apply_*`: utiles pero peligrosos.
- Importadores EUR-Lex/BOE: sensibles por vigencia y cambios de fuente.

## Scripts existentes y uso recomendado

### Seguros / read-only

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

### Dry-run por defecto o preparados para no escribir

```powershell
python scripts/migrate_study_features.py --dry-run
python scripts/apply_mapping_review.py reports/mapping_review_template.csv --dry-run
python scripts/long_task_monitor.py -- <comando>
python scripts/qa_session_report.py
```

### Tests

```powershell
python scripts/test_mapping_tools.py
python scripts/test_study_features.py
```

### Sensibles: no usar sin permiso

```powershell
python scripts/apply_mapping_review.py --apply
python scripts/apply_a1_article_validation.py
python scripts/apply_pilot_lpac_delimitation.py
python scripts/apply_fase2b_lrjsp_lcsp_delimitation.py
python scripts/import_official_sources.py
python scripts/import_eurlex_direct.py
python scripts/import_topics_and_validate_coverage.py
python scripts/normalize_articles_inplace.py
python scripts/normalize_articles_pass2.py
python scripts/normalize_articles_pass3.py
python scripts/normalize_articles_pass4.py
```

## Como validar cambios

Base:

```powershell
python -m compileall app.py src scripts
python scripts/validate_article_quality.py
python scripts/app_healthcheck.py
```

Mapping:

```powershell
python scripts/report_mapping_status.py
python scripts/audit_existing_fine_mappings.py
python scripts/validate_mapping_review.py reports/mapping_review_template.csv
```

Study backend:

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

## Rollback

### Codigo

Revertir solo cambios propios. No usar `git reset --hard`.

### BD

1. Cerrar Streamlit.
2. Localizar backup en `db/backups`.
3. Sustituir `db/gvadicto.sqlite` por backup.
4. Ejecutar:

```powershell
python scripts/validate_article_quality.py
python scripts/report_mapping_status.py
```

### Reports

Los reports son derivados. Se pueden regenerar.

## Como continuar desarrollo

1. Determinar si la tarea es juridica, UI, estudio u operaciones.
2. Si es juridica, usar nivel alto/extremo y fuentes oficiales.
3. Si es UI/backend, mantener vertical slices pequenas.
4. Antes de cualquier escritura de BD, tomar hash y backup.
5. Ejecutar validaciones especificas.

## Como continuar mappings

1. Revisar `reports/mapping_status.md`.
2. Usar `reports/mapping_review_template.csv`.
3. Rellenar solo filas con fuente clara.
4. Validar:

```powershell
python scripts/validate_mapping_review.py reports/mapping_review_template.csv
python scripts/apply_mapping_review.py reports/mapping_review_template.csv --dry-run
```

5. Aplicar solo con permiso:

```powershell
python scripts/apply_mapping_review.py reports/mapping_review_template.csv --apply
```

No inventar articulos. No usar rangos genericos si la plantilla pide `article_id`.

## Como integrar StudyService

Documentos:

- `docs/STUDY_FEATURES_BACKEND.md`
- `docs/STUDY_FEATURES_UI_INTEGRATION_PLAN.md`

Pasos:

1. Pedir permiso para migracion real.
2. Ejecutar:

```powershell
python scripts/migrate_study_features.py --apply
python scripts/report_study_features.py
```

3. Integrar en `app.py` solo en pestana Estudiar.
4. Capturar `StudySchemaMissingError`.
5. Mantener `study_annotations` hasta migrar datos o retirar UI legacy.

## Como integrar launcher

Pendiente. No hay launcher final consolidado.

Recomendacion futura:

- Crear script PowerShell que haga `cd` al repo y lance `python -m streamlit run app.py`.
- Crear generador `.lnk` con dry-run y `--create`.
- Usar icono `assets/icons/gvadictos.ico` cuando exista.
- Documentar en `docs/LAUNCHER_WINDOWS.md`.

## Como integrar branding

Estado:

- Nombre objetivo visible: `GVAdictos`.
- Quedan restos historicos y User-Agent `GVAdicto/0.1` en scripts sensibles.

Regla:

- Cambiar textos visibles primero.
- No renombrar paquetes/rutas sin necesidad.
- No tocar scripts juridicos mientras Claude trabaje imports/mappings.

## Como integrar tipografia, temas y assets

Pendiente. Crear despues de estabilizar UI:

- `src/ui/theme.py`
- `src/ui/typography.py`
- `src/ui/assets.py`
- `assets/logo`
- `assets/icons`
- `assets/splash`
- `assets/images`

No copiar assets desde Descargas hasta que el usuario lo pida.

## Riesgos abiertos

- `app.py` demasiado grande.
- Mappings y anotaciones dependen de `article_id`.
- Reimportaciones pueden regenerar articulos.
- Doble capa `src/studies` y `src/study`.
- Reports pueden quedarse desactualizados.
- Documentacion historica puede contradecir estado real.
- Scripts peligrosos no tienen una interfaz comun de confirmacion.

## Bugs abiertos o sospechas

- Branding no completamente limpio.
- UI densa y con tablas largas.
- `study_annotations` no escala a highlights/progreso avanzados.
- No hay migraciones versionadas.
- No hay tests visuales automatizados.
- No hay gestion de concurrencia si Claude/Codex/Streamlit escriben a la vez.

## TODO recomendado

1. Terminar calidad de datos y mappings activos.
2. Congelar scripts peligrosos con dry-run/backups.
3. Aplicar StudyService con migracion real autorizada.
4. Refactorizar `app.py` por componentes.
5. Limpiar branding visible.
6. Crear tema/tipografia/assets.
7. Crear launcher Windows.
8. Mejorar accesibilidad.
9. Mejorar exportaciones.

