# Prompt para ClaudeCode

Estoy trabajando en el repositorio GitHub/local `IsaacGaRos/GVAdictos`, foco real A1-01 GVA 2025.

Lee primero, sin leer todo el repo:

1. `CLAUDE.md`
2. `docs/CLAUDE_HANDOFF.md`
3. `.claude/NEXT_CHAT_START_HERE.md`
4. `docs/STUDY_INTERFACE_SPEC.md`
5. `app.py` solo en las funciones de Estudio si vas a tocar UI

Estado que debes asumir:

- Codex ya completo la validacion juridica de articulos para temas 8, 17, 18, 21, 32, 52, 54 y 55 en `.claude/VALIDACION_ARTICULOS_POR_TEMA.md`.
- Codex ya importo Reglamento de Les Corts BOE 2026 desde `BOE-A-2026-5880`.
- Codex ya aplico mapeos en SQLite con `scripts/apply_a1_article_validation.py`.
- `topic_sources.mapping_basis = validacion_articulos_codex_2026_06_18`.
- No rehagas esa validacion salvo duda concreta.

Cambios tecnicos ya hechos:

- Nuevo script idempotente: `scripts/apply_a1_article_validation.py`.
- El script no reimporta Reglamento Les Corts BOE 2026 si el hash no ha cambiado y ya hay articulos, para no regenerar `article_id` innecesariamente.
- Nueva fuente oficial local:
  - `data/sources/leyes_originales/BOE/BOE-A-2026-5880_Reglamento_Les_Corts_2026.html`
  - `data/processed/official_sources/BOE-A-2026-5880.txt`
- `app.py` corregido: Estudio usa `article_id` cuando hay mapeos finos y solo cae a `law_id` cuando no hay mapeo por articulo.
- Anotacion minima persistente implementada: tabla `study_annotations`, CRUD en `src/studies/annotations.py` y UI en Estudiar para nota/subrayado/duda/marcador vinculados a tema o articulo visible.
- BD actual: 81 leyes, 11509 articulos, 75 temas, 742 `topic_sources`, 21 hallazgos abiertos.

Verificacion ya ejecutada:

```powershell
python scripts/import_official_sources.py
python scripts/apply_a1_article_validation.py
python -m compileall app.py src scripts
python scripts/check_source_updates.py --source-kind boe_html
git diff --check
```

Tambien se probo CRUD real de `study_annotations` y Streamlit responde en `http://localhost:8501`.

Tarea inmediata recomendada:

1. Ejecuta `streamlit run app.py`.
2. Verifica visualmente la pestana Estudiar:
   - Tema general 8 debe mostrar Reglamento Les Corts BOE 2026 arts. 112-139 como fuente principal.
   - Tema especial 21 debe mostrar 114 articulos LCSP delimitados, no toda la ley.
   - Tema especial 32 debe mostrar 114 articulos LGSS delimitados.
3. Si eso esta correcto, implementa una mejora pequena sobre Estudiar. No rehagas la anotacion minima.

Siguientes vertical slices posibles:

- filtros y contadores de anotaciones por tipo/articulo;
- Pomodoro personalizable dentro de Estudiar;
- accion contextual futura: seleccionar fragmento y preguntar duda a IA con modo mock/fallback;
- NO implementar remapeo avanzado de anotaciones todavia.

Reglas:

- No modificar originales oficiales.
- No inventar contenido juridico.
- No generar preguntas nuevas todavia salvo que se pida.
- Cualquier contenido juridico generado por IA debe tener fuente y `requiere_revision = 1`.
- Trabaja por vertical slice pequena y verificable.

Nivel recomendado:

- Orientacion y prueba visual: medio.
- Mejoras simples de anotaciones o Pomodoro: medio/alto.
- Remapeo de anotaciones tras cambios normativos: extremadamente alto, pero NO hacerlo ahora.

Formato de respuesta antes de tocar codigo:

- Modelo recomendado:
- Motivo:
- Archivos minimos a leer:
- Archivos probables a modificar:
- Plan minimo en 3-5 pasos:
- Verificacion:
- Riesgos:

Formato despues de tocar codigo:

- Cambios realizados:
- Archivos modificados:
- Como ejecutarlo:
- Verificacion hecha:
- Riesgos pendientes:
- Siguiente tarea recomendada:
- PROJECT_STATE actualizado en formato breve.
