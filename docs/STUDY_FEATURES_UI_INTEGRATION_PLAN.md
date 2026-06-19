# Study features UI integration plan

Contrato para integrar el backend de estudio en `app.py` cuando el usuario autorice la migracion real.

## Estado actual

El backend existe en:

- `src/study/schema.py`
- `src/study/repository.py`
- `src/study/service.py`

La migracion real NO esta aplicada por defecto.
Primero comprobar:

```powershell
python scripts/migrate_study_features.py --dry-run
python scripts/report_study_features.py
```

Aplicar solo con autorizacion expresa:

```powershell
python scripts/migrate_study_features.py --apply
```

## Inicializar servicio

Ejemplo para futura UI:

```python
from src.core.db import connect
from src.study.repository import StudyRepository, StudySchemaMissingError
from src.study.service import StudyService, StudyTarget

with connect() as conn:
    service = StudyService(StudyRepository(conn))
```

Si la BD no esta migrada, los metodos lanzan `StudySchemaMissingError`.
La UI debe capturarlo y mostrar un aviso discreto: funcionalidades de estudio pendientes de activar.

## Funciones publicas de `StudyService`

### `add_article_note`

Input:

```python
note_id = service.add_article_note(
    article_id=article_id,
    note_text="Mi nota",
    selected_text="texto seleccionado",
    anchor_key="articulo-3-parrafo-2",
    tags="plazo;importante",
)
```

Output: `int` con `note_id`.

Errores esperados:

- `StudySchemaMissingError` si no hay migracion.
- `ValueError` si `article_id` no existe.
- `ValueError` si `note_text` esta vacio.

### `update_article_note`

Input:

```python
service.update_article_note(
    note_id=note_id,
    note_text="Nota actualizada",
    selected_text="nuevo texto",
    anchor_key="articulo-3-parrafo-3",
    tags="repasar",
)
```

Output: `None`.

### `delete_article_note`

Borrado logico mediante `archived_at`.

```python
service.delete_article_note(note_id)
```

Output: `None`.

### `add_highlight`

Input:

```python
highlight_id = service.add_highlight(
    article_id=article_id,
    selected_text="fragmento subrayado",
    color="yellow",
    anchor_key="articulo-3-parrafo-2",
    start_offset=120,
    end_offset=180,
    note_text="Sale mucho",
)
```

Output: `int` con `highlight_id`.

Colores permitidos:

- `yellow`
- `green`
- `blue`
- `pink`
- `purple`
- `red`

### `update_highlight`

```python
service.update_highlight(
    highlight_id=highlight_id,
    selected_text="fragmento actualizado",
    color="green",
    anchor_key="articulo-3-parrafo-2",
    start_offset=120,
    end_offset=190,
    note_text="Prioridad alta",
)
```

Output: `None`.

### `delete_highlight`

Borrado logico mediante `archived_at`.

```python
service.delete_highlight(highlight_id)
```

Output: `None`.

### `mark`

Marcar duda/importante/bookmark en articulo o tema.

```python
service.mark(
    StudyTarget(article_id=article_id),
    mark_type="important",
    note_text="Prioritario",
)

service.mark(
    StudyTarget(article_id=article_id),
    mark_type="doubt",
    note_text="Preguntar a IA",
)
```

Output: `int` con `mark_id`.

Tipos permitidos:

- `doubt`
- `important`
- `bookmark`

Para resolver una duda:

```python
service.mark(
    StudyTarget(article_id=article_id),
    mark_type="doubt",
    resolved=True,
)
```

### `set_progress`

```python
service.set_progress(
    StudyTarget(article_id=article_id),
    status="reviewing",
    completion_percent=60,
    minutes_delta=25,
    pomodoro_delta=1,
)
```

Output: `int` con `progress_id`.

Estados permitidos:

- `not_started`
- `reading`
- `reviewing`
- `completed`
- `paused`

### `record_review`

```python
service.record_review(
    StudyTarget(article_id=article_id),
    result="good",
    confidence=4,
    next_review_at="2026-06-25",
    notes="Revisar antes de simulacro",
)
```

Output: `int` con `review_id`.

Resultados permitidos:

- `unknown`
- `again`
- `hard`
- `good`
- `easy`

### `get_article_state`

```python
state = service.get_article_state(article_id)
```

Output:

```python
{
    "article_id": 123,
    "notes": [...],
    "highlights": [...],
    "marks": [...],
    "progress": {...} | None,
    "last_review": {...} | None,
}
```

Uso UI:

- mostrar notas debajo del articulo,
- renderizar highlights,
- mostrar chips de duda/importante,
- mostrar barra de progreso,
- mostrar fecha de ultima revision.

### `get_topic_summary`

```python
summary = service.get_topic_summary(topic_id)
```

Output:

```python
{
    "topic_id": 10,
    "article_count": 12,
    "notes": 3,
    "highlights": 8,
    "doubt_marks": 1,
    "important_marks": 4,
    "progress_average": 75.0,
    "topic_progress": {...} | None,
    "topic_marks": [...],
    "topic_last_review": {...} | None,
    "latest_review": {...} | None,
}
```

### `get_law_summary`

```python
summary = service.get_law_summary(law_id)
```

Output similar a resumen por tema, agregado por articulos de una norma.

## Manejo de BD no migrada

Patron recomendado:

```python
try:
    state = service.get_article_state(article_id)
except StudySchemaMissingError:
    state = None
    st.info("Funciones de estudio pendientes de activar.")
```

No crear tablas desde la UI.
No lanzar `migrate_study_features.py --apply` desde `app.py`.

## Que NO debe tocar la UI

- No modificar `articles`.
- No modificar `topic_sources`.
- No reimportar normas.
- No recalcular mapping juridico.
- No ejecutar normalizadores.
- No aplicar migraciones automaticas al abrir la app.

## Siguiente vertical slice recomendada

1. Pedir autorizacion para aplicar migracion real.
2. Ejecutar:

```powershell
python scripts/migrate_study_features.py --apply
python scripts/report_study_features.py
```

3. En `app.py`, dentro de Estudio:
   - inicializar `StudyService`,
   - capturar `StudySchemaMissingError`,
   - mostrar panel de notas y highlights por articulo,
   - botones/chips para duda/importante,
   - selector de estado de progreso,
   - boton de revision rapida `again/hard/good/easy`.

4. Verificar con:

```powershell
python -m compileall src scripts
python scripts/test_study_features.py
python scripts/report_study_features.py
streamlit run app.py
```
