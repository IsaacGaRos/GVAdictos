# Mensaje inicial para Claude Code

Lee primero:

1. `docs/CLAUDE_KNOWLEDGE_DUMP.md`
2. `docs/CLAUDE_CODE_HANDOFF.md`
3. El documento especifico de la tarea actual

Reglas base:

- No inventar contenido juridico.
- No tocar `articles`, `topic_sources`, parser/importer, normalizacion ni BD sin permiso explicito.
- Para mappings, usar primero dry-run y validacion.
- Para UI/StudyService, no aplicar migraciones sin autorizacion.

Estado read-only observado el 2026-06-18:

- 81 leyes.
- 6792 articulos.
- 75 temas.
- 1286 `topic_sources`.
- 1079 enlaces con `article_id`.
- 16 temas con mapping fino.

Ultimo avance aplicado:

- Fase 2E PE-13 aplicada con `mapping_basis = validacion_articulos_claude_fase2e_pe13_2026_06_18`.
- PE-13 (`topic_id=28`): Ley 40/2015 arts. 1-53 y 140-158; Decreto 176/2014 arts. 1-21.
- Validacion posterior: `validate_article_quality.py` PASS; FKs rotas 0.
