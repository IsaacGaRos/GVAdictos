# Ola D — IA y Multimedia (Completada 2026-06-19)

## Resumen ejecutivo

Completada la **Ola D** (IA y multimedia) con 5 entregables integrados en la UI:

- **D1**: Adaptador LLM con Claude API, prompts versionados y caché por hash
- **D2**: 6 tipos de insights contextuales por artículo
- **D3**: Generación de preguntas test (4 estilos)
- **D4**: TTS con Web Speech API nativa del navegador
- **D5**: Mapa de relaciones entre artículos (búsqueda semántica MVP)

## Módulos creados

```
src/ai/
  ├── __init__.py
  ├── schema.py          # ai_article_insights, ai_prompt_cache
  ├── repository.py      # CRUD insights + caché
  ├── service.py         # AIService (adaptador Claude)
  ├── prompts.py         # 6 prompts versionados (v1.0)
  └── ui.py              # render_ai_insights, render_ai_question_generator

src/audio/
  ├── __init__.py
  ├── schema.py          # tts_audio tabla
  ├── repository.py      # CRUD TTS
  ├── service.py         # TTSService
  └── ui.py              # render_tts_player (Web Speech API)

src/search/
  ├── __init__.py
  ├── schema.py          # article_embeddings, article_relations
  ├── repository.py      # CRUD relaciones + similitud
  ├── service.py         # SearchService
  └── ui.py              # render_related_articles
```

## Tablas de BD creadas

### AI (src/ai)
- `ai_article_insights` (id, article_id, insight_type, content, model, prompt_version, input_hash, requiere_revision, validation_status, created_at)
- `ai_prompt_cache` (input_hash, prompt_type, output_text, model, tokens_used, expires_at)

### AI Questions (src/ai, extendido)
- `ai_questions` (article_id, topic_id, estilo, enunciado, respuesta_correcta, explicacion, requiere_revision, validation_status)
- `ai_question_options` (ai_question_id, letra, texto, es_correcta)

### Audio (src/audio)
- `tts_audio` (scope_type, scope_id, voice, speed, content_hash, storage_url, duration_seconds)

### Search (src/search)
- `article_embeddings` (article_id, model, dimension, embedding_vector, computed_at)
- `article_relations` (from_article_id, to_article_id, relation_type, weight, source)

## Características implementadas

### D1 — Adaptador LLM
- ✓ Inicialización de cliente Anthropic
- ✓ Prompts versionados (v1.0) con consistencia
- ✓ Caché automática por input_hash (sha256)
- ✓ Control de coste (coste por token estimado)
- ✓ Manejo de errores y API timeout

### D2 — Insights contextuales (6 tipos)
1. **Explicación sencilla**: para alumnos sin formación jurídica
2. **Resumen estructurado**: con concepto clave + elementos + aplicación
3. **Mnemotecnia**: acrónimos y técnicas de memorización
4. **Comparación**: con otros artículos relacionados
5. **Errores comunes**: malinterpretaciones frecuentes
6. **Qué suele preguntarse**: aspectos de alta probabilidad en exámenes

Todas marcan `requiere_revision=1` por defecto (pendiente validación humana).

### D3 — Generación de preguntas (4 estilos)
- **Normal**: comprensión media
- **Difícil**: conocimiento detallado
- **Oficial**: formato exacto de oposición (4 opciones A-D)
- **Trampa**: sutilezas que confunden

Parseo de respuesta según formato especificado en prompt.
Todas marcan `requiere_revision=1`.

### D4 — TTS (Texto a Voz)
- ✓ Web Speech API nativa (sin coste, navegador)
- ✓ Controles: reproducir, pausar, detener
- ✓ Velocidad ajustable (0.5x a 2.0x)
- ✓ Estimación de duración (fórmula: 130 wpm base para legal)
- ✓ Almacenamiento de metadatos en BD

MVP usa navegador. Future: cloud TTS con caché.

### D5 — Búsqueda semántica + relaciones
- ✓ Tablas para embeddings y relaciones
- ✓ CRUD de relaciones (cita, desarrolla, concordancia, similar_semantica)
- ✓ Búsqueda de artículos relacionados
- ✓ Búsqueda de citantes
- ✓ Mapa bidireccional (incoming/outgoing)

MVP: relaciones explícitas. Future: búsqueda por embeddings (pgvector).

## Integración UI

Todas las características están integradas en la pestaña **"Estudiar"** bajo cada artículo renderizado:

```
┌─────────────────────────────────┐
│ Art. XX - Título del artículo   │
├─────────────────────────────────┤
│ [Texto del artículo...]          │
├─────────────────────────────────┤
│ ▼ Ampliación y notas            │
│ ▼ Insights IA (Ola D2)          │
│ ▼ Generar pregunta IA (Ola D3)  │
│ ▼ Escuchar (TTS - Ola D4)       │
│ ▼ Artículos relacionados (Ola D5)│
└─────────────────────────────────┘
```

## Scripts de migración

```bash
python scripts/migrate_ai_features.py --apply          # Crea tablas ai_*
python scripts/migrate_ai_features.py --apply          # Crea ai_questions*
python scripts/migrate_audio_features.py --apply       # Crea tts_audio
python scripts/migrate_search_features.py --apply      # Crea article_*
```

## Configuración requerida

### Para IA (D2, D3)
```bash
export ANTHROPIC_API_KEY="sk-ant-..."  # Required para usar IA
```

Sin esta variable, los expanders de IA muestran aviso de no configurado.

### Para TTS (D4)
- ✓ Sin configuración: usa Web Speech API del navegador (MVP)
- Soporta cualquier navegador moderno con Web Speech API

### Para búsqueda (D5)
- ✓ Sin configuración: muestra relaciones existentes (MVP)
- Future: agregará embeddings automáticos

## Decisiones de arquitectura

1. **Caché por hash**: Reduce costes de IA y garantiza reproducibilidad
2. **Prompts versionados**: Permite auditoría y reproducción de outputs
3. **requiere_revision=1 por defecto**: Todo contenido IA pendiente validación
4. **Web Speech MVP**: Sin coste, sin dependencias externas, acceso inmediato
5. **Relaciones explícitas**: Base para futuro search semántico

## Riesgos mitigados

- ✓ Coste descontrolado: caché + hashing
- ✓ Inconsistencia: prompts versionados
- ✓ Hallucinations: `requiere_revision` + fuente obligatoria
- ✓ Fragilidad: fallbacks a BD existentes si IA no disponible
- ✓ Performance: índices en tablas de IA

## Limitaciones conocidas

- **D2-D3**: Requiere ANTHROPIC_API_KEY configurada
- **D4**: Solo Web Speech API (futuro: cloud TTS)
- **D5**: Relaciones manuales o importadas (futuro: embeddings)
- **UI**: Expanders bajo cada artículo (sin interfaz dedicada)

## Próximas olas

- **Ola E**: Modo examen, versionado legislativo, monitor normativo
- **Ola F**: Multiusuario, API FastAPI, Postgres

## Commit de referencia

```
8bdc130 Ola D3-D5 completa: Generación de preguntas IA + TTS + Búsqueda semántica
02415ca Ola D1-D2: Adaptador IA + Insights contextuales
```
