# Documentation Audit

No se ha borrado documentacion. Esta auditoria clasifica que existe y como usarlo.

## Documentos principales recomendados

- `docs/CLAUDE_KNOWLEDGE_DUMP.md`: primer documento para Claude al iniciar sesion.
- `docs/CLAUDE_CODE_HANDOFF.md`: handoff amplio con estado, scripts y riesgos.
- `docs/PROJECT_ARCHITECTURE.md`: arquitectura y flujos.
- `docs/TECHNICAL_ROADMAP.md`: orden tecnico recomendado.
- `docs/DEVELOPMENT_CONVENTIONS.md`: guia de trabajo.

## Documentos utiles por area

### Juridico / mapping

- `docs/A1_LEGISLATION_AUDIT.md`
- `docs/MAPPING_WORKFLOW.md`
- `docs/CLAUDE_MAPPING_TOOLS_HANDOFF.md`
- `reports/mapping_status.md`
- `reports/fallback_topics.csv`
- `reports/existing_fine_mappings.csv`

### Estudio

- `docs/STUDY_INTERFACE_SPEC.md`
- `docs/STUDY_FEATURES_BACKEND.md`
- `docs/STUDY_FEATURES_UI_INTEGRATION_PLAN.md`

### Operaciones

- `docs/LONG_TASKS_AND_BROWSERBATCH_RUNBOOK.md`
- `docs/CLAUDE_LONG_TASK_HANDOFF.md`
- `reports/app_healthcheck.md`
- `logs/long_task_*.log`

### Producto / UX

- `docs/UI_ARCHITECTURE.md`
- `docs/BRANDING_GUIDE.md`
- `docs/ROADMAP.md`

## Documentos potencialmente obsoletos o solapados

- `docs/CLAUDE_HANDOFF.md`: util, pero puede quedar por detras de `docs/CLAUDE_CODE_HANDOFF.md`.
- `docs/CLAUDE_START_PROMPT.md`: corto, puede apuntar al knowledge dump nuevo.
- `docs/CODEX_SESSION_SUMMARY.md`: historico; no usar como estado unico.
- `.claude/*`: util para sesiones concretas, pero puede mezclar estados anteriores.
- `README.md`: introduccion general, no sustituye handoff tecnico.
- `docs/ROADMAP.md`: roadmap antiguo y breve; preferir `docs/TECHNICAL_ROADMAP.md`.

## Contradicciones detectadas

- Nombre historico `GVAdicto` frente a nombre objetivo `GVAdictos`.
- Referencias C2 historicas frente a foco actual A1-01 GVA 2025.
- `study_annotations` MVP actual frente a backend nuevo `src/study`.
- Algunos reports reflejan estados antiguos porque Claude siguio aplicando mappings despues.

## Documentacion faltante

- Guia de launcher Windows final con comando confirmado e icono real.
- Guia de tema/tipografia/assets final cuando se decida visualmente.
- Politica de versionado de reports.
- Procedimiento formal de migraciones con tabla `schema_migrations`.
- Matriz de scripts seguros/peligrosos automatizada.

## Recomendacion

Claude debe leer primero:

1. `docs/CLAUDE_KNOWLEDGE_DUMP.md`
2. `docs/CLAUDE_CODE_HANDOFF.md`
3. `docs/PROJECT_ARCHITECTURE.md`
4. Documento especifico de la tarea.

Claude debe evitar usar como fuente primaria documentos historicos salvo para contexto.

