# Technical Debt

Clasificacion consolidada para continuar con Claude Code.

## Critica

### Scripts que escriben en BD y pueden pisar trabajo paralelo

Riesgo: alto si se ejecutan mientras Claude delimita normativa.

Ejemplos:

- `scripts/apply_a1_article_validation.py`
- `scripts/apply_pilot_lpac_delimitation.py`
- `scripts/apply_fase2b_lrjsp_lcsp_delimitation.py`
- `scripts/import_topics_and_validate_coverage.py`
- `scripts/import_official_sources.py`
- `scripts/import_eurlex_direct.py`
- normalizadores `scripts/normalize_articles_*.py`

Mejora: exigir dry-run/backup/handoff explicito en todos los scripts con escritura.

### Parser/importador sensible

`src/laws/importer.py` es critico porque puede regenerar `article_id` y afectar anotaciones/mappings.

Mejora: congelar pruebas de regresion antes de cualquier cambio.

### `app.py` monolitico

`app.py` mezcla consultas, renderizado, formularios, anotaciones, test y exportaciones.

Mejora: extraer componentes por pestana despues de cerrar trabajo juridico activo.

## Alta

### Doble sistema de estudio

Existen:

- `src/studies/annotations.py` con tabla actual `study_annotations`.
- `src/study/*` con backend nuevo propuesto para notas/highlights/progreso.

Riesgo: confusion si se integran ambos sin plan de migracion.

Mejora: decidir si `study_annotations` queda como legacy o se migra a tablas nuevas.

### Documentacion solapada

Hay varios handoffs y snapshots:

- `docs/CLAUDE_HANDOFF.md`
- `docs/CLAUDE_START_PROMPT.md`
- `docs/CODEX_SESSION_SUMMARY.md`
- `.claude/*`

Riesgo: Claude lea un documento antiguo y use estado desactualizado.

Mejora: priorizar `docs/CLAUDE_PROJECT_HANDOFF.md` y `docs/CLAUDE_KNOWLEDGE_DUMP.md`.

### Naming historico

Quedan restos de `GVAdicto` y referencias C2 historicas en docs/scripts.

Mejora: limpiar solo textos visibles y dejar nombres internos si romper imports no compensa.

### Reports generados versionados

`reports/` contiene salidas de ejecuciones puntuales. Algunas son utiles, otras envejecen.

Mejora: definir que reports se versionan y cuales son artefactos locales.

## Media

### Scripts sin interfaz comun

Cada script maneja CLI, DB, reports y errores de forma distinta.

Mejora: crear utilidades compartidas para hash, conexion read-only, escritura de reports y backups.

### Falta test suite central

Hay scripts de test, no framework unico.

Mejora: mantener scripts simples ahora; migrar a pytest cuando el MVP se estabilice.

### Falta contrato UI estable

StudyService tiene contrato documentado, pero `app.py` aun no lo usa.

Mejora: integrar por vertical slice solo tras migracion aprobada.

### Falta gestion formal de migraciones

`init_db` crea tablas base; nuevas tablas usan scripts separados.

Mejora: crear tabla `schema_migrations` solo cuando haya varias migraciones reales.

## Baja

### Paquetes placeholder

`planner`, `notifications`, `simulacros`, `watchers`, `anki` estan poco desarrollados.

Mejora: mantener hasta que haya necesidad real.

### Estilos y branding sin sistema aplicado

Hay docs, pero no sistema visual integrado.

Mejora: abordarlo despues de StudyService y UI.

### Launcher Windows pendiente

No hay launcher definitivo ni icono final.

Mejora: crear acceso directo solo cuando haya icono y flujo estable.

## Zonas fragiles

- Reimportar leyes puede cambiar `article_id`.
- Normalizar articulos puede romper mappings/anotaciones si no se remapea.
- Mappings juridicos requieren fuente y revision humana.
- Streamlit puede recargar durante cambios de archivo.
- Automatizaciones semanales deben apuntar al mismo hilo/chat, no abrir contextos dispersos.

