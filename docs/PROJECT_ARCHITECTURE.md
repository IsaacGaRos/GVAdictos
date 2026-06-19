# GVAdictos Project Architecture

Fecha de consolidacion: 2026-06-18.

Este documento resume la arquitectura sin exigir leer todo el codigo.

## Objetivo del proyecto

GVAdictos es una aplicacion local-first para estudiar la oposicion A1-01 GVA 2025. El producto combina normativa oficial, delimitacion tema -> norma -> articulo, lectura por temas, preguntas tipo test con fuente, fallos, reports y futuras funciones de estudio personal.

## Estado de datos observado

Consulta read-only sobre `db/gvadicto.sqlite`:

- `laws`: 81.
- `articles`: 6792.
- `topics`: 75.
- `topic_sources`: 1192.
- `topic_sources` con `article_id`: 985.
- Temas con mapping fino: 15.
- `questions`: 20.
- `attempts`: 0.
- `study_annotations`: 0.
- `source_documents`: 157.
- `source_update_checks`: 206.
- `topic_validation_findings`: 32.

## Dependencias

Runtime principal:

- Python.
- Streamlit.
- SQLite.
- pandas.
- pypdf.

Dependencias declaradas en `requirements.txt`:

```text
streamlit>=1.34
pandas>=2.0
pypdf>=5.0
```

## Estructura de carpetas

- `app.py`: UI Streamlit monolitica actual.
- `src/core`: rutas, conexion SQLite, exportaciones y catalogo de fuentes.
- `src/laws`: parser/importador de normas a tabla `laws` y `articles`.
- `src/tests`: CRUD de preguntas tipo test.
- `src/mistakes`: intentos, fallos y resumen semanal.
- `src/reports`: metricas basicas del dashboard.
- `src/studies`: anotaciones MVP actuales usadas por `app.py`.
- `src/study`: backend nuevo y separado para notas, highlights, progreso, marcas y ultima revision. No migrado en BD real.
- `src/anki`: paquete placeholder.
- `src/planner`, `src/notifications`, `src/simulacros`, `src/watchers`: paquetes placeholder o preparatorios.
- `scripts`: importacion, auditoria, validacion, mapping, monitorizacion y utilidades.
- `docs`: documentacion funcional, juridica, handoffs y runbooks.
- `reports`: informes generados por scripts.
- `data/sources`: manifiestos, convocatoria A1-01, inventarios Drive y fuentes originales.
- `data/processed`: textos procesados.
- `db`: SQLite y backups.
- `logs`: logs de tareas largas.
- `Archivo Oposicion TAG-GVA`: material local academico/historico; puede estar desactualizado.

## Modulos principales

### `src/core/paths.py`

Define rutas raiz: `ROOT_DIR`, `DB_PATH`, `EXPORTS_DIR`, `LAW_SOURCES_DIR`.

### `src/core/db.py`

Define `connect`, `init_db`, `fetch_all`, `fetch_one`.

Tablas base:

- `laws`
- `articles`
- `questions`
- `attempts`
- `study_annotations`
- `source_documents`
- `source_update_checks`
- `topics`
- `topic_sources`
- `topic_validation_findings`

### `src/laws/importer.py`

Importa textos normativos a `laws` y `articles`. Es zona sensible: no tocar sin pruebas de calidad y backup. Contiene parser de articulos.

### `src/core/source_catalog.py`

Importa y lista fuentes externas en `source_documents`.

### `src/tests/repository.py`

CRUD de preguntas: crear, actualizar, borrar, listar y recuperar preguntas.

### `src/mistakes/repository.py`

Registra intentos y genera resumen de fallos y evolucion semanal.

### `src/studies/annotations.py`

Backend MVP actual para anotaciones simples vinculadas a tema/articulo en `study_annotations`.

### `src/study`

Backend nuevo de estudio, todavia no aplicado a la BD real:

- `schema.py`: tablas propuestas.
- `repository.py`: acceso a datos.
- `service.py`: validaciones de dominio.

Tablas propuestas:

- `study_article_notes`
- `study_highlights`
- `study_progress`
- `study_marks`
- `study_last_reviews`

## Flujo de datos

1. Fuentes oficiales o academicas se catalogan en CSV/manifiestos.
2. Scripts de importacion convierten fuentes a texto cuando procede.
3. `src/laws/importer.py` crea una fila `laws` y multiples filas `articles`.
4. `topics` contiene el temario oficial A1-01.
5. `topic_sources` vincula temas con normas y, cuando ya hay delimitacion fina, con `article_id`.
6. `app.py` consume `topics`, `topic_sources`, `laws` y `articles` para estudiar.
7. Preguntas manuales o controladas van a `questions`.
8. Intentos del modo test van a `attempts`.
9. Anotaciones MVP van a `study_annotations`.
10. Backend futuro de estudio usara tablas `src/study/schema.py` tras migracion autorizada.

## Flujo de importacion

1. Fuente original queda bajo `data/sources/leyes_originales`.
2. Fuente procesada queda bajo `data/processed`.
3. Scripts como `import_official_sources.py`, `import_eurlex_direct.py` o `import_law.py` llaman al importador.
4. El importador calcula hash, parsea articulos y refresca filas de `articles` para esa norma.
5. `validate_article_quality.py` verifica duplicados, articulos vacios, cabeceras anidadas, indices y FKs.

## Flujo de mapping

1. `topic_sources` arranca con enlaces tema-norma.
2. Scripts de delimitacion aprobados por revision humana incorporan `article_id`.
3. Scripts de auditoria generan `reports/fallback_topics.*`, `existing_fine_mappings.*`, `mapping_status.*`.
4. Plantilla `mapping_review_template.csv` permite revisar futuros mappings.
5. No aplicar cambios con `apply_mapping_review.py --apply` sin autorizacion expresa.

## Flujo de estudio actual

1. Usuario abre pestana Estudiar.
2. Selecciona parte general/especial.
3. Selecciona tema.
4. UI lista normas vinculadas.
5. Si hay mapping fino para norma/tema, muestra articulos delimitados.
6. Si no hay mapping fino, muestra fallback explicito y no presenta toda la norma como si fuera temario validado.
7. Anotaciones MVP se guardan en `study_annotations`.

## Flujo UI

`app.py` usa Streamlit directamente:

- `st.tabs` para secciones.
- `st.dataframe` para tablas.
- `st.selectbox`, `st.radio`, `st.text_input`, `st.text_area` para formularios.
- `st.expander` para edicion y vista avanzada.
- Helpers internos cargan datos desde SQLite.

## Zonas estables

- Conexion SQLite basica.
- CRUD preguntas.
- Registro de intentos.
- Export CSV/Anki basico.
- Auditorias de mapping en dry-run.
- Healthcheck, monitor de tareas largas y diagnostico Streamlit.

## Zonas experimentales

- Parser/importador de articulos tras normalizaciones recientes.
- Delimitaciones juridicas automatizadas o semi-automatizadas.
- Backend `src/study` hasta aplicar migracion real.
- UI de estudio avanzada.
- Launcher/branding/tema/tipografia/assets: documentado, no integrado.

