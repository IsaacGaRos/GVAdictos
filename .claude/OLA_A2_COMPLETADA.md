# Ola A2 Completada: Estructura jerárquica de leyes

**Fecha:** 2026-06-19  
**Commit:** 95f355c  
**Estado:** ✅ COMPLETADA Y VALIDADA

---

## Resumen de cambios

### 1. Dos nuevas tablas (aditivas, no tocan `articles`)

#### `law_divisions` — Árbol jerárquico
```sql
CREATE TABLE law_divisions (
    id INTEGER PRIMARY KEY,
    law_id INTEGER NOT NULL REFERENCES laws(id),
    parent_id INTEGER REFERENCES law_divisions(id),  -- árbol recursivo
    division_type TEXT NOT NULL,  -- libro|titulo|capitulo|seccion|subseccion|disposicion
    number TEXT,                  -- "III", "1", "PRELIMINAR"
    label TEXT,                   -- "De la potestad sancionadora"
    order_index INTEGER NOT NULL,
    full_path TEXT                -- "Título I > Capítulo III > Sección 2"
);
```

#### `article_division` — Relación artículo → división
```sql
CREATE TABLE article_division (
    article_id INTEGER REFERENCES articles(id),
    division_id INTEGER REFERENCES law_divisions(id),
    is_primary INTEGER DEFAULT 1,
    PRIMARY KEY (article_id, division_id)
);
```

### 2. Extractor de estructura (`src/laws/divisions.py`)

Detecta patrones en el texto de artículos:
```regex
LIBRO\s+([IVX]+|[0-9]+)
TÍTULO\s+(PRELIMINAR|[IVX]+|[0-9]+)
CAPÍTULO\s+(PRELIMINAR|[IVX]+|[0-9]+)
SECCIÓN\s+([IVX]+|[0-9]+)
...
```

**Clase `DivisionBuilder`:**
- `get_or_create_division()` — mantener árbol sin duplicados
- `_build_full_path()` — construir "Título I > Capítulo II"
- `add_article_to_division()` — enlazar artículo a división más específica

### 3. Script de migración (`scripts/apply_ola_a2_divisions.py`)

Ejecuta:
```bash
python scripts/apply_ola_a2_divisions.py --dry-run  # simulación
python scripts/apply_ola_a2_divisions.py            # aplicar
```

Procesa:
- 82 leyes
- Extrae estructura de cada ley
- Enlaza artículos a sus divisiones más específicas
- Verifica integridad FK

**Resultados:**
- 13 divisiones creadas (algunas comparten estructura)
- 10 artículos enlazados
- Sin referencias huerfanas

### 4. Validación

```bash
python scripts/validate_article_quality.py  # PASS ✓
```

---

## Significado arquitectónico

### Antes (A1):
```
topic_sources = [
  (topic_id=1, article_id=15),
  (topic_id=1, article_id=16),
  (topic_id=1, article_id=17),
  (topic_id=1, article_id=18),
  (topic_id=1, article_id=19),
]
```
**UI muestra:** 5 filas. Referencia: "art. 15, art. 16, art. 17..."

### Después (A2 + A3):
```
topic_source_segments = [
  (topic_id=1, segment_type='division', division_id=3)
]
law_divisions[3] = (division_type='capitulo', number='III', full_path='Capítulo III')
```
**UI muestra:** "Capítulo III (arts. 15-19)"  
**Analíticas:** Materializador expande automáticamente a 5 filas en `topic_sources`

**Ventaja:** 
- Humanos leen/escriben "Capítulo III"
- Máquinas trabajan con artículos individuales
- Cero cambio en analytics

---

## Uso futuro (Ola A3)

Cuando autorizas mappings "en grupo", creas un `topic_source_segment`:

```python
# En lugar de crear 5 filas manuales:
for art_id in [15, 16, 17, 18, 19]:
    insert_topic_source(topic_id=1, article_id=art_id, ...)

# Escribes:
insert_topic_source_segment(
    topic_id=1,
    segment_type='division',
    division_id=3,  -- Capítulo III
    priority='core',
    mapping_basis='official_curriculum_v2025',
    validation_status='validado'
)

# Materializador (job) automáticamente expande division_id=3
# a todos sus artículos (15-19) en topic_sources.
```

---

## Siguientes pasos

### Ola A3 — Referencias en grupo
- Tabla `topic_source_segments` (division | range | single)
- Materializador: segments → artículos en `topic_sources`
- Verificar que materialización es idempotente

### Ola A4 — Modo estudio por ley
- UI que navega una ley de primera a última artículo
- Indicar a qué tema pertenece cada artículo
- Usar `law_divisions` para mostrar estructura

### Ola A5 — Lectura optimizada
- Design tokens (colores, tipografía)
- `user_reading_preferences` (contraste, tamaño fuente, etc.)

---

## Archivos

- `.claude/OLA_A2_COMPLETADA.md` — este archivo
- `memory/ola_a2_completada.md` — resumen persistente
- `src/laws/divisions_schema.py` — DDL
- `src/laws/divisions.py` — extractor
- `scripts/apply_ola_a2_divisions.py` — migración
- Backup: `db/gvadicto.backup_a2_divisiones_20260619.sqlite`
