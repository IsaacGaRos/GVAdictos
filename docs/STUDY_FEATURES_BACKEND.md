# Study features backend

Backend preparado para funciones de estudio local-first sin tocar mapping juridico.
La migracion es dry-run por defecto y las pruebas usan SQLite en memoria.

## Alcance

Incluye tablas separadas para:

- notas por articulo,
- subrayados/highlights,
- estado de estudio,
- marcas de duda/importante/marcador,
- ultima revision.

No modifica:

- `articles`,
- `topic_sources`,
- parser/importadores,
- normativa,
- mapping juridico.

## Tablas propuestas

### `study_article_notes`

Notas vinculadas a articulo.

Campos clave:

- `article_id`
- `law_id_snapshot`
- `article_ref_snapshot`
- `anchor_key`
- `selected_text`
- `note_text`
- `tags`
- `created_at`
- `updated_at`
- `archived_at`

Los snapshots permiten conservar contexto si en el futuro se remapean articulos.

### `study_highlights`

Subrayados por articulo.

Campos clave:

- `article_id`
- `law_id_snapshot`
- `article_ref_snapshot`
- `anchor_key`
- `selected_text`
- `start_offset`
- `end_offset`
- `color`
- `note_text`
- `archived_at`

Colores soportados: `yellow`, `green`, `blue`, `pink`, `purple`, `red`.

### `study_progress`

Estado de estudio por tema o articulo.

Campos clave:

- `topic_id`
- `article_id`
- `status`
- `completion_percent`
- `total_minutes`
- `pomodoro_count`
- `last_activity_at`

Estados soportados:

- `not_started`
- `reading`
- `reviewing`
- `completed`
- `paused`

### `study_marks`

Marcas de trabajo.

Tipos:

- `doubt`
- `important`
- `bookmark`

Campos clave:

- `topic_id`
- `article_id`
- `mark_type`
- `note_text`
- `resolved`

### `study_last_reviews`

Ultima revision por tema o articulo.

Campos clave:

- `topic_id`
- `article_id`
- `last_reviewed_at`
- `last_result`
- `confidence`
- `next_review_at`
- `review_count`
- `notes`

Resultados soportados:

- `unknown`
- `again`
- `hard`
- `good`
- `easy`

## Migracion

Dry-run:

```powershell
python scripts/migrate_study_features.py --dry-run
```

Tambien es dry-run si no se pasa `--apply`.

Aplicacion futura, solo con autorizacion expresa:

```powershell
python scripts/migrate_study_features.py --apply
```

`--apply` crea backup en `db/backups/` antes de crear tablas.

## Helpers

### `src/study/repository.py`

Repositorio de bajo nivel. Recibe una conexion `sqlite3.Connection`.

Operaciones principales:

- crear/listar/archivar notas,
- crear/listar/archivar highlights,
- upsert de progreso,
- upsert/listado de marcas,
- upsert/consulta de ultima revision,
- conteos.

### `src/study/service.py`

Capa de servicio con validaciones:

- objetivo con `topic_id` o `article_id`,
- textos no vacios,
- colores permitidos,
- estados de progreso permitidos,
- tipos de marca permitidos,
- resultados de revision permitidos,
- porcentajes y confianza en rango.

## Tests

```powershell
python scripts/test_study_features.py
```

Usan SQLite en memoria. No tocan la BD real.

Cubren:

- creacion de esquema,
- notas,
- highlights,
- progreso,
- marcas,
- ultima revision,
- validaciones negativas,
- conteos.

## Report

```powershell
python scripts/report_study_features.py
```

Genera:

- `reports/study_features_status.md`
- `reports/study_features_status.json`

El report es read-only. Si no se ha aplicado migracion, mostrara tablas pendientes.

## Siguiente paso UI

Integrar vertical slice en la interfaz de estudio:

1. Ejecutar migracion real solo tras aprobacion.
2. Usar `StudyRepository` + `StudyService`.
3. En vista de articulo:
   - panel de notas,
   - boton de highlight,
   - marcas duda/importante,
   - estado de progreso,
   - ultima revision.
4. No mezclar estas tablas con `topic_sources` ni con contenido juridico generado.
5. Mantener futuras tareas de remapeo de anotaciones como capa separada.
