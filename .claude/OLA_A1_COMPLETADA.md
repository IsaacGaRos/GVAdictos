# Ola A1 Completada: Migrar src/study a BD real

**Fecha:** 2026-06-19  
**Commit:** 475dbf9  
**Estado:** ✅ COMPLETADA Y VALIDADA

---

## Resumen de cambios

### 1. Schema de BD (src/study/schema.py)
5 nuevas tablas con índices y patrón anchor_key/snapshot:

```sql
study_article_notes      -- notas en artículos (con selected_text, anchor_key)
study_highlights         -- subrayados con color (yellow|green|blue|pink|purple|red)
study_progress           -- progreso por tema/artículo (estado, minutos, pomodoros)
study_marks              -- dudas, importante, marcadores (mark_type, resolved)
study_last_reviews       -- historial SRS (next_review_at, confidence, review_count)
```

**Patrón de anclaje:** Cada anotación guarda `anchor_key` + `law_id_snapshot` + `article_ref_snapshot`. Permite que las anotaciones sobrevivan cambios de versión legislativa (mapeo de anclajes en Ola E2).

### 2. Capas de código

- **`src/study/repository.py`** — CRUD completo (20+ métodos)
  - `create_article_note`, `update_article_note`, `list_article_notes`, `archive_article_note`
  - `create_highlight`, `update_highlight`, `list_highlights`, `archive_highlight`
  - `upsert_progress`, `get_progress`
  - `upsert_mark`, `list_marks`
  - `record_last_review`, `get_last_review`
  - Helpers: `get_article_study_state`, `get_topic_summary`, `get_law_summary`

- **`src/study/service.py`** — Capa de dominio
  - `add_article_note`, `update_article_note`, `delete_article_note`
  - `add_highlight`, `update_highlight`, `delete_highlight`
  - `set_progress`, `mark`, `record_review`
  - Validaciones: longitud (max 20k), colores, estados, rangos
  - Excepciones específicas: `StudyStorageError`, `StudySchemaMissingError`

### 3. Migración de datos

**Script:** `scripts/apply_ola_a1_study_migration.py`

Opciones:
```bash
python scripts/apply_ola_a1_study_migration.py --dry-run  # simulación
python scripts/apply_ola_a1_study_migration.py            # aplicar
```

Mapeo de anotaciones antiguas (si existen):
- `annotation_type='note'` → `study_article_notes`
- `annotation_type='highlight'` → `study_highlights`
- `annotation_type='doubt'` → `study_marks(mark_type='doubt')`
- `annotation_type='bookmark'` → `study_marks(mark_type='bookmark')`

### 4. Compatibilidad

**`src/studies/annotations.py` reescrito:**
- Funciones públicas (`create_annotation`, `update_annotation`, `delete_annotation`, `get_annotations_for_topic`) ahora delegan a `StudyService`
- Devuelven datos en formato compatible con la UI
- app.py **NO NECESITA CAMBIOS** (usa las mismas funciones)

### 5. Validación

```bash
python scripts/validate_article_quality.py  # PASS ✓
```

**Resultados:**
- 5 tablas creadas ✓
- Todos los índices en lugar ✓
- FK correctas ✓
- Estructura de datos compatible con delimitación 75/75 ✓

---

## Uso desde la UI

Después de Ola A1, la pestaña "Estudiar" de Streamlit permite:

```python
# Crear nota en un artículo
from src.studies.annotations import create_annotation
note_id = create_annotation(
    topic_id=None,
    article_id=123,
    annotation_type="note",
    note_text="Recordar que...",
    selected_text="fragmento",
    anchor_key="art_123_art-25-1"  # opcional
)

# Crear subrayado
highlight_id = create_annotation(
    topic_id=None,
    article_id=123,
    annotation_type="highlight",
    selected_text="texto importante",
    color="yellow"
)

# Obtener anotaciones de un tema
annotations = get_annotations_for_topic(topic_id=1)
# Devuelve lista de dicts con: id, topic_id, article_id, annotation_type, 
#                              selected_text, note_text, color, article_ref, law_name, updated_at
```

---

## Significado arquitectónico

Ola A1 es **fundamental** para todo lo que viene:

1. **Anclaje por `anchor_key`** (Ola E2)
   - Cuando la legislación cambia de versión, las anotaciones no se pierden
   - Se remapean inteligentemente al nuevo `anchor_key`

2. **SRS tipo Anki** (Ola C1)
   - `study_last_reviews` es la tabla base directa
   - `next_review_at`, `last_result`, `confidence`, `review_count` están listos
   - Solo falta lógica SM-2 en servicio

3. **Plan diario inteligente** (Ola C2)
   - `study_progress` con minutos/pomodoros ya rastreados
   - `study_marks` con dudas/importantes
   - Base para generar plan adaptativo

4. **UI por tipo de anotación** (Ola A4+)
   - Notas = discusión libre
   - Highlights = visualización en texto
   - Marks = dudas/importantes para repaso priorizado

---

## Backup

Antes de aplicar la migración se hizo backup:
```
db/gvadicto.backup_a1_inicio_20260619.sqlite
```

Si algo sale mal, revert es trivial:
```bash
cp db/gvadicto.backup_a1_inicio_20260619.sqlite db/gvadicto.sqlite
```

---

## Siguientes pasos

**Ola A2 — Estructura jerárquica**
- Crear `law_divisions` (libro > título > capítulo > sección > subsección)
- Extractor de capítulos/secciones del text de artículos
- Enlace `article_division` (qué división contiene cada artículo)

**Ola A3 — Referencias en grupo**
- Tabla `topic_source_segments` (division | range | single)
- Materializador: segmentos → filas en `topic_sources`
- UI: "arts. 25-31 (Cap. III)" en lugar de 7 filas

**Ola B — Banco de exámenes**
- Esquema + convocatorias piloto
- Vinculación pregunta→artículo (same rigor as fine mapping)

**Ola C — SRS y plan diario**
- SM-2 sobre `study_last_reviews`
- Generador de plan: SRS vencidas + errores + importancia

---

## Cambios en .claude/

Próxima sesión comienza aquí. El prompt de arranque está en:
`.claude/NEXT_CHAT_START_HERE.md` (actualizado con estado A1)

Memoria local: `memory/ola_a1_completada.md`
