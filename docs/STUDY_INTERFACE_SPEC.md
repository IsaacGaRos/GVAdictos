# Especificacion - Interfaz de estudio GVAdictos

Fecha: 2026-06-17

## Objetivo

GVAdictos debe evolucionar desde un MVP de importacion normativa y preguntas a una app de estudio completa para oposiciones GVA.

La app debe abrir el repositorio/local workspace y ofrecer un apartado de estudio donde el opositor pueda:

- Ver todos los temas oficiales ordenados.
- Separar claramente parte general y parte especifica.
- Entrar en cada tema.
- Ver exactamente que normativa entra en ese tema.
- Estudiar esa normativa preparada, estructurada y trazada a fuente.
- Editar su material de estudio: subrayados, notas, marcas, comentarios, dudas, etiquetas y otros cambios tipicos.
- Mantener esas ediciones aunque se actualice normativa o temario cuando el contenido base siga igual.
- Detectar cambios normativos y comparar version anterior vs nueva para recolocar o revisar trabajo personal.
- Usar Pomodoro personalizable dentro del entorno de estudio.

## Principios

- Local-first: SQLite y archivos locales.
- Fuente oficial primero: BOE, DOGV, EUR-Lex.
- Material academico/Drive solo como apoyo, no como autoridad juridica.
- No modificar originales oficiales en `data/sources/leyes_originales`.
- Las anotaciones del usuario deben vivir separadas del texto oficial.
- Si una norma cambia, no se destruye el trabajo del usuario: se conserva, se intenta remapear y se muestra la diferencia.
- Todo contenido juridico generado o resumido por IA debe quedar marcado como `requiere_revision`.

## Experiencia deseada

### Pantalla principal de estudio

Debe mostrar:

- Parte general.
- Parte especifica.
- Temas numerados segun temario oficial.
- Estado por tema: no empezado, en curso, revisado, con cambios normativos pendientes, con dudas, con preguntas generadas.
- Progreso: tiempo estudiado, sesiones, ultima revision, fallos asociados y porcentaje de acierto si existen preguntas.

### Vista de tema

Al entrar en un tema debe aparecer:

- Enunciado oficial del tema.
- Bloque: parte general o parte especifica.
- Normativa que entra, con fuente oficial.
- Articulos/bloques concretos asociados al tema.
- Material preparado para estudiar: texto oficial, epigrafes, articulos clave, notas, dudas, preguntas vinculadas e historial de cambios.

### Editor/anotador

Debe permitir:

- Subrayar texto con colores.
- Marcar texto como importante.
- Añadir notas marginales.
- Añadir dudas.
- Añadir etiquetas.
- Marcar fragmentos como `memorizar`, `repasar`, `preguntable` o `confuso`.
- Crear una pregunta desde un fragmento seleccionado.
- Seleccionar un fragmento y abrir una accion contextual para preguntar una duda a la IA.
- Ocultar/mostrar anotaciones.
- Filtrar por tipo de marca.

Las anotaciones deben guardarse sin modificar el texto oficial.

### Dudas con IA sobre seleccion

Idea de producto: al seleccionar una parte del texto de estudio, el usuario debe poder abrir una accion contextual, idealmente click derecho si la tecnologia lo permite, para preguntar una duda a la IA sobre ese fragmento.

Reglas:

- Debe enviarse a la IA el fragmento seleccionado, norma, articulo/bloque, tema y fuente local.
- La respuesta no puede modificar el texto oficial.
- La duda y respuesta deben guardarse como anotacion vinculada al fragmento.
- Toda respuesta juridica generada por IA debe marcarse como `requiere_revision`.
- Si no hay API configurada, debe existir modo mock/fallback que prepare el prompt o guarde la duda sin responder.
- La UI puede usar un boton contextual equivalente si Streamlit no permite click derecho de forma fiable en la primera version.

## Persistencia ante actualizaciones

Cuando una fuente oficial se actualice:

1. Se conserva la version anterior.
2. Se importa la nueva version.
3. Se comparan bloques/articulos.
4. Si un bloque no cambia, sus anotaciones se mantienen automaticamente.
5. Si un bloque cambia parcialmente, se intenta remapear la anotacion por ancla textual.
6. Si no se puede remapear con seguridad, se marca como `requiere_revision`.
7. El usuario puede ver texto anterior, texto nuevo, diferencias, anotaciones previas y anotaciones remapeadas.

## Estrategia tecnica para anotaciones robustas

No basta con guardar posiciones `start/end`, porque una actualizacion normativa puede mover texto.

Cada anotacion deberia guardar:

- `source_document_id`.
- `law_id`.
- `article_id`.
- `content_version_id`.
- Tipo: highlight, note, doubt, ai_doubt, tag, bookmark, question_seed.
- `start_offset` y `end_offset`.
- Texto seleccionado exacto.
- `prefix_context` y `suffix_context`.
- Hash del bloque/articulo en el momento de anotar.
- Estado de remapeo: `active`, `remapped`, `needs_review`, `orphaned`.
- Color, etiquetas, nota y duda.

Para remapear tras una actualizacion:

- Si el hash del articulo/bloque no cambia: mantener anotaciones.
- Si cambia: buscar texto seleccionado exacto en el nuevo bloque.
- Si hay una unica coincidencia: remapear.
- Si hay varias: usar prefix/suffix.
- Si no hay coincidencia exacta: usar similitud textual limitada.
- Si la confianza es baja: marcar `needs_review`.

## Tablas propuestas

`topics` y `topic_sources` ya existen en SQLite. El resto de tablas son propuesta para fase 2 y deben implementarse de forma incremental.

### `topics`

- `id`
- `official_number`
- `part` (`general`, `especial`)
- `block_name`
- `title`
- `official_text`
- `source_document_id`
- `status`

### `topic_sources`

- `id`
- `topic_id`
- `law_id`
- `article_id`
- `coverage_status`
- `priority`
- `notes`
- `validation_status`

### `content_versions`

- `id`
- `source_document_id`
- `law_id`
- `article_id`
- `content_hash`
- `text`
- `valid_from`
- `imported_at`
- `previous_version_id`

### `annotations`

- `id`
- `topic_id`
- `law_id`
- `article_id`
- `content_version_id`
- `annotation_type`
- `selected_text`
- `prefix_context`
- `suffix_context`
- `start_offset`
- `end_offset`
- `color`
- `note`
- `tags`
- `status`
- `created_at`
- `updated_at`

### `annotation_remap_events`

- `id`
- `annotation_id`
- `from_content_version_id`
- `to_content_version_id`
- `status`
- `confidence`
- `old_selected_text`
- `new_selected_text`
- `diff_summary`
- `created_at`

### `study_sessions`

- `id`
- `topic_id`
- `started_at`
- `ended_at`
- `duration_seconds`
- `mode`
- `notes`

### `pomodoro_settings`

- `id`
- `profile_name`
- `work_minutes`
- `short_break_minutes`
- `long_break_minutes`
- `cycles_before_long_break`
- `sound_enabled`
- `auto_start_breaks`
- `auto_start_work`

### `pomodoro_sessions`

- `id`
- `topic_id`
- `started_at`
- `ended_at`
- `work_seconds`
- `break_seconds`
- `completed_cycles`
- `interrupted`
- `notes`

## Pomodoro

La interfaz de estudio debe incluir:

- Temporizador visible.
- Configuracion de trabajo, descanso corto, descanso largo y ciclos.
- Sonido/notificacion configurable.
- Inicio automatico o manual.
- Asociar sesion Pomodoro a tema.
- Guardar tiempo real de estudio.
- Permitir pausar, cancelar y registrar interrupcion.

## Fases de implementacion recomendadas

### Fase 2.1 - Navegador de temas

- Crear tablas `topics` y `topic_sources`.
- Importar `a1_01_2025_temario_oficial_extraido.csv`.
- Mostrar pantalla de estudio con parte general/especifica.
- Abrir vista de tema con normativa asociada desde `a1_01_2025_cobertura_normativa.csv`.

### Fase 2.2 - Vista de lectura

- Mostrar articulos/bloques relacionados con el tema.
- Filtros por norma.
- Busqueda dentro del tema.
- Marcadores simples por articulo.

### Fase 2.3 - Anotaciones basicas

- Subrayado por fragmento.
- Notas por fragmento.
- Dudas.
- Etiquetas.
- Persistencia SQLite.

### Fase 2.4 - Versionado y remapeo

- Crear `content_versions`.
- Guardar versiones al reimportar fuentes.
- Remapear anotaciones si el hash no cambia.
- Implementar diff visual para bloques cambiados.

### Fase 2.5 - Pomodoro

- Crear ajustes y sesiones.
- Temporizador en la vista de estudio.
- Guardar sesiones por tema.

### Fase 2.6 - Preguntas desde estudio

- Crear preguntas desde fragmentos anotados.
- Vincular pregunta a tema, articulo y seleccion.
- Marcar `requiere_revision`.

## Siguiente paso concreto

Antes de implementar anotaciones, construir el navegador de temas:

1. Crear tablas `topics` y `topic_sources`.
2. Cargar los 75 temas oficiales.
3. Vincular cobertura normativa existente.
4. Añadir nueva pestaña o seccion `Estudiar` en Streamlit.
5. Mostrar parte general y parte especifica.
6. Entrar en un tema y ver normativa/articulos asociados.

Nivel recomendado: alto.

Para versionado/anotaciones robustas: extremadamente alto.
