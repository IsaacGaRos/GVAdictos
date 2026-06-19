# Roadmap

## Fase 1 - MVP funcional

Implementada en version inicial.

## Fase 2 - Estudio real

- Interfaz de estudio por temas oficiales.
- Separacion parte general / parte especifica.
- Vista de tema con normativa concreta aplicable.
- Subrayados, notas, dudas y etiquetas persistentes.
- Pomodoro personalizable dentro del entorno de estudio.
- Base de fallos avanzada.
- Repeticion espaciada.
- Simulacros.
- Exportacion Anki mejorada.
- Planificador basico.
- Importacion de planificacion de academia.

## Fase 3 - Adaptacion

- Versionado de contenido normativo.
- Remapeo de anotaciones tras actualizaciones.
- Comparacion visual entre version anterior y nueva.
- Planificacion adaptativa por rendimiento.
- Pesos por articulo/bloque.
- Reajuste por dias perdidos.
- Dashboard semanal.

## Fase 4 - Automatizacion

- Watcher de convocatorias.
- Watcher normativo.
- Google Calendar/Tasks/ICS.
- Informes automaticos.

## Fase 5 - Funcionalidades estrategicas (diseno, no implementar aun)

Dos funcionalidades de alto valor disenadas para fases futuras. No se implementan
ahora para no interferir con el freeze arquitectonico ni con la estabilizacion de
datos juridicos. Quedan especificadas a nivel de estructura de datos y arquitectura.

### 5.1 Banco oficial de examenes A1-01 GVA

Objetivo: base de datos con TODOS los examenes oficiales A1-01 GVA de convocatorias
anteriores, con respuestas oficiales cuando existan, y analitica de frecuencias para
priorizar el estudio.

- Prioridad recomendada: ALTA (es la fuente con mayor poder predictivo real de examen;
  encaja con la senal Autentica ya usada para priorizar).
- Dependencias:
  - Catalogo de temas A1-01 ya existente (`topics`).
  - Articulos normalizados y delimitacion fina tema->norma->articulo (`topic_sources.article_id`)
    -> idealmente >= 30-40 temas mapeados para que la analitica por articulo sea util.
  - Cierre de la estabilizacion de datos (Ley 40/2015) antes de cruzar preguntas con articulos.
  - Fuente: examenes oficiales publicados (PDF/plantillas DOGV/GVA). Entrada manual o semi-automatica.
- Arquitectura de datos propuesta (nuevas tablas SQLite, no rompen el esquema actual):
  - `exam_papers(id, convocatoria, anio, bloque, fase, fuente_oficial_url, fuente_path,
    estado, validation_status, notes)`
  - `exam_questions(id, exam_paper_id FK, numero, enunciado, es_reserva,
    respuesta_oficial, anulada, validation_status)`
  - `exam_question_options(id, exam_question_id FK, letra, texto, es_correcta)`
  - `exam_question_links(id, exam_question_id FK, topic_id FK, law_id FK,
    article_id FK NULL, tipo_relacion, mapping_basis, confianza, validation_status)`
    -> reutiliza el patron de `topic_sources` (FK a `articles.id`, mapping_basis trazable,
    pendiente_de_validacion por defecto).
  - Vistas/consultas analiticas derivadas (no tablas): frecuencia por ley, por articulo,
    por tema, por bloque; repeticion entre convocatorias; evolucion historica.
- Metricas calculables: articulos mas preguntados, leyes mas importantes historicamente,
  temas con mayor peso real, tendencia temporal del contenido preguntado.
- Uso posterior: priorizacion de estudio, badges de importancia en modo Estudio,
  generacion de preguntas tipo test ancladas a examenes oficiales (con `requiere_revision=1`).
- Impacto esperado: convierte la priorizacion de "intuicion/Autentica" en datos objetivos;
  alimenta repeticion espaciada y simulacros con peso real.
- Riesgos: calidad/derechos de los PDF oficiales; preguntas anuladas o con plantilla revisada;
  vinculacion pregunta->articulo es trabajo juridico (mismo rigor que la delimitacion fina);
  no inventar el articulo si la pregunta no lo cita de forma inequivoca.
- Momento optimo: tras cerrar la estabilizacion de Ley 40/2015 y alcanzar masa critica de
  delimitacion fina (para que el cruce pregunta->articulo sea fiable). Empezar por 1-2
  convocatorias piloto antes de cargar el historico completo.

### 5.2 Monitor inteligente de convocatorias (amplia el "Watcher de convocatorias" de Fase 4)

Objetivo: supervisar automaticamente futuras convocatorias A1-01 GVA y avisar de cambios,
comparando cada nueva convocatoria con la anterior.

- Prioridad recomendada: MEDIA (critico solo cuando se abra una nueva convocatoria; util de
  forma continua para no perder publicaciones).
- Dependencias:
  - Infraestructura de watchers ya prevista (`src/watchers/`, `scripts/check_source_updates.py`).
  - Fuentes oficiales estables (DOGV, sede GVA, BOE) y politica de no romper originales.
  - Idealmente, snapshot versionado de la convocatoria vigente para diffs.
- Eventos a detectar: nueva convocatoria, modificacion de bases, cambios de temario,
  alta/baja de leyes, cambios de requisitos, cambios de fases.
- Publicaciones a vigilar/avisar: convocatoria, bases, correcciones, listas provisionales y
  definitivas, tribunal, fechas/sedes de examen, plantillas de respuestas, resultados,
  resoluciones relevantes.
- Arquitectura recomendada:
  - Fuentes -> fetch (reutiliza watchers) -> normalizacion a texto -> snapshot con hash.
  - `convocatoria_snapshots(id, convocatoria, fuente, fetched_at, hash, path)`.
  - Motor de diff que compara temario y catalogo de normas nueva vs anterior y genera
    informe: que cambia, normas nuevas/eliminadas, articulos a revisar, impacto sobre estudio.
  - Canal de alertas: informe local + integracion opcional Calendar/Tasks/ICS (ya en Fase 4).
- Impacto esperado: cero riesgo de perder una publicacion oficial; actualizacion guiada del
  temario y de las normas vigiladas; informe de impacto sobre el material de estudio.
- Riesgos: dependencia de la estructura web/PDF de las fuentes (fragil ante rediseños);
  falsos positivos en diffs; requiere fuente oficial (no academia) para decisiones de vigencia.
- Momento optimo: activar la deteccion/alertas de publicaciones de forma continua en Fase 4;
  el comparador automatico de temario/normas, cuando se anuncie o se aproxime una nueva
  convocatoria (es cuando aporta valor real).
