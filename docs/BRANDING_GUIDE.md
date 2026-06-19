# Branding Guide

## Nombre visible

El nombre visible unico debe ser:

```text
GVAdictos
```

No usar en textos visibles:

- `GVAdicto`
- `GVAdicto local`
- variantes con singular

## Situacion actual

Documentos actualizados en sesiones recientes:

- `README.md`: titulo y descripcion inicial.
- `AGENTS.md`: titulo y objetivo.
- `CLAUDE.md`: titulo y objetivo.
- `src/__init__.py` y `src/core/__init__.py`: docstrings.
- `docs/STUDY_INTERFACE_SPEC.md`: titulo e introduccion.
- `docs/DRIVE_IMPORT_CANDIDATES.md`: textos visibles.
- `docs/A1_LEGISLATION_AUDIT.md`: nombre de automatizacion documentada.

Nota de consolidacion: `app.py` no se modifica en esta fase final. La limpieza de titulo visible de Streamlit queda pendiente para una tarea UI/branding dedicada.

## Pendiente por prudencia

Quedan referencias `GVAdicto/0.1` como User-Agent en scripts de descarga/importacion normativa.
No se han tocado porque el usuario pidio no interferir con importer/parser/mapping juridico.

Tambien puede haber referencias historicas en logs o reports ya generados. No se reescriben para preservar trazabilidad.

## Metadatos recomendados

- App name: `GVAdictos`
- Window title: `GVAdictos`
- Shortcut name: `GVAdictos.lnk`
- Icon expected path: `assets/icons/gvadictos.ico`
- Favicon expected path: `assets/icons/favicon.ico`

## Quick Wins

1. Importar `APP_NAME` desde `src/ui/branding.py` en `app.py`.
2. Sustituir textos de marca restantes en documentos activos.
3. Cambiar User-Agent solo cuando Claude no este trabajando en importadores juridicos.
4. Regenerar reports historicos solo si el usuario pide limpieza documental.

## Riesgos

- Cambiar nombres internos de paquete o rutas puede romper imports.
- Reescribir logs/reports historicos puede ocultar contexto de auditoria.
- Cambiar scripts de descarga durante trabajo juridico paralelo puede interferir con Claude.

## Orden recomendado

1. Mantener `GVAdictos` en UI visible.
2. Actualizar docs vivos.
3. Auditar scripts juridicos al final de la fase de mappings.
4. Congelar una convencion: nombres internos pueden seguir estables si no son visibles.
