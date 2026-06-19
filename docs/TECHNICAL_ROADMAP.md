# Technical Roadmap

Roadmap recomendado tras la consolidacion Codex.

## 1. Calidad de datos

Objetivo: asegurar que leyes, articulos, temas y mappings estan limpios, trazados y actualizados.

Dependencias:

- Claude debe terminar delimitacion LRJSP/LCSP y siguientes bloques.
- `validate_article_quality.py`.
- Reports de mapping.

Riesgo: critico. Cualquier reimportacion puede afectar `article_id`.

Tiempo estimado: 1-3 sesiones largas por bloque juridico.

## 2. Integracion StudyService

Objetivo: activar backend de estudio moderno: notas, highlights, marcas, progreso y ultima revision.

Dependencias:

- Autorizacion para `python scripts/migrate_study_features.py --apply`.
- Tests de `scripts/test_study_features.py`.
- Plan `docs/STUDY_FEATURES_UI_INTEGRATION_PLAN.md`.

Riesgo: alto. Hay que convivir con `study_annotations` legacy.

Tiempo estimado: 1 sesion para migracion y backend; 1-2 sesiones para UI.

## 3. UI

Objetivo: convertir la pestana Estudiar en experiencia de estudio pulida.

Dependencias:

- StudyService migrado.
- Datos de mapping suficientes.
- QA visual con Streamlit.

Riesgo: alto por `app.py` monolitico.

Tiempo estimado: 2-4 sesiones.

## 4. Branding

Objetivo: nombre visible `GVAdictos`, logo, favicon e identidad consistente.

Dependencias:

- Decidir si se limpian scripts juridicos con User-Agent antiguo.
- Assets finales del usuario.

Riesgo: medio. Cambiar nombres internos puede romper imports; limitar a textos visibles.

Tiempo estimado: 0.5-1 sesion.

## 5. Launcher

Objetivo: abrir la app desde acceso directo Windows.

Dependencias:

- Icono `.ico`.
- Puerto y comando de arranque estabilizados.
- Documentacion `docs/LAUNCHER_WINDOWS.md` pendiente de completar o regenerar.

Riesgo: medio por diferencias de entorno Python/venv.

Tiempo estimado: 0.5 sesion.

## 6. Accesibilidad

Objetivo: legibilidad, contraste, navegacion por teclado y ergonomia de formularios.

Dependencias:

- UI mas modular.
- Tema/tipografia definidos.
- QA visual.

Riesgo: medio.

Tiempo estimado: 1-2 sesiones.

## 7. Rendimiento

Objetivo: reducir carga de tablas grandes, queries repetidas y render pesado de articulos.

Dependencias:

- Perfilado de Streamlit.
- Indices SQLite revisados.
- Cache controlada.

Riesgo: medio si se cachean datos juridicos desactualizados.

Tiempo estimado: 1-2 sesiones.

## 8. Exportaciones

Objetivo: mejorar CSV/Anki y preparar exportaciones de progreso/estudio.

Dependencias:

- StudyService integrado.
- Modelo de datos de estudio estable.

Riesgo: bajo/medio.

Tiempo estimado: 1 sesion.

## 9. Funcionalidades futuras

Objetivo: Pomodoro, preguntas con fuente por tema validado, IA contextual, comparador normativo, repeticion espaciada.

Dependencias:

- Datos juridicos fiables.
- StudyService.
- UI estable.
- Politica de fuentes y revision.

Riesgo: alto para IA juridica y remapeo normativo.

Tiempo estimado: incremental por vertical slices.

