# Handoff para Claude - herramientas de mapping fino

## Estado generado por Codex

Codex ha creado una suite tecnica para apoyar la delimitacion fina tema -> norma -> articulo sin aplicar delimitaciones juridicas.

No se ha reimportado normativa, no se ha tocado `articles`, no se ha modificado `app.py` y no se ha ejecutado ningun `--apply`.

Estado actual observado en los reports:

- Total temas: 75.
- Temas con algun mapping fino: 12.
- Temas sin mapping fino: 63.
- Estados de tema: mapped=11, partial=1, fallback=57, ambiguous=6.
- Grupos tema-norma: 177.
- Mappings finos existentes: 661 filas con `article_id`.
- Integridad de mappings finos existentes: ok=661.
- `mapping_basis` existentes principales:
  - `validacion_articulos_codex_2026_06_18`: 535 filas.
  - `delimitacion_convocatoria_titulos_claudecode_2026_06_18`: 126 filas.

Nota: durante la sesion se detecto que `db/gvadicto.sqlite` cambio por trabajo paralelo antes de ejecutar la suite final. Desde el baseline operativo actual, hash SHA256 `8B4F4606A04B010EBC3079450A9AC6E8AB2ABBE31F49015F242398A7AA25241D`, las validaciones y dry-run no cambiaron la BD.

## Scripts nuevos

- `scripts/mapping_tools.py`: utilidades compartidas read-only, clasificacion, validacion y planificacion.
- `scripts/report_mapping_status.py`: genera estado global.
- `scripts/audit_fallback_topics.py`: genera auditoria de fallback/partial/ambiguous.
- `scripts/audit_existing_fine_mappings.py`: baseline de mappings finos existentes.
- `scripts/generate_mapping_review_template.py`: plantilla CSV para revision juridica.
- `scripts/validate_mapping_review.py`: valida plantilla revisada sin escribir en BD.
- `scripts/apply_mapping_review.py`: dry-run por defecto; solo escribe con `--apply`.
- `scripts/test_mapping_tools.py`: checks negativos y hash sin cambios.

## Reports generados

- `reports/mapping_status.md`
- `reports/mapping_status.json`
- `reports/fallback_topics.md`
- `reports/fallback_topics.csv`
- `reports/existing_fine_mappings.md`
- `reports/existing_fine_mappings.csv`
- `reports/mapping_review_template.csv`
- `reports/apply_mapping_review_<timestamp>.md`
- `reports/apply_mapping_review_<timestamp>.json`

## Verificacion ejecutada

```powershell
python -m compileall scripts
python scripts/report_mapping_status.py
python scripts/audit_fallback_topics.py
python scripts/audit_existing_fine_mappings.py
python scripts/generate_mapping_review_template.py
python scripts/validate_mapping_review.py reports/mapping_review_template.csv
python scripts/apply_mapping_review.py reports/mapping_review_template.csv --dry-run
python scripts/test_mapping_tools.py
```

Resultado relevante:

- Plantilla: 177 filas.
- Validacion plantilla: 0 errores, 6 warnings por filas no aprobadas sin `law_id`.
- Dry-run: 0 mappings planificados porque la plantilla aun no esta aprobada.
- Tests: pasan; detectan `article_id` inexistente, `article_id` de otra norma, aprobado sin articulos e intento de sobrescribir mapping protegido.

## Reglas para Claude

- No rellenar `article_ids_to_apply` sin fuente.
- No usar rangos genericos en `article_ids_to_apply`.
- No marcar `approved = 1` sin `autentica_reference` o `review_notes`.
- No sobrescribir mappings con `mapping_basis = validacion_articulos_codex_2026_06_18`.
- No ejecutar `--apply` sin autorizacion del usuario.
- Si una fila esta ambigua o sin `law_id`, resolver primero la asociacion tema-norma antes de aprobar.

## Prompt sugerido para Claude

Estoy trabajando en `IsaacGaRos/GVAdictos`.

Ya existe una suite tecnica de apoyo al mapping fino creada por Codex. No debes auditar todo el repo: lee solo:

- `docs/MAPPING_WORKFLOW.md`
- `docs/CLAUDE_MAPPING_TOOLS_HANDOFF.md`
- `reports/mapping_status.md`
- `reports/fallback_topics.csv`
- `reports/mapping_review_template.csv`

Objetivo actual: usar Autentica/CEF/fuente oficial para rellenar progresivamente `reports/mapping_review_template.csv` con articulos exactos por tema-norma, sin inventar mappings.

Reglas:

- No ejecutes `--apply`.
- No modifiques `db/gvadicto.sqlite`.
- No toques `articles`.
- No reimportes normas.
- No uses rangos genericos.
- Cada fila aprobada debe tener `approved = 1`, `article_ids_to_apply` con ids explicitos, y `autentica_reference` o `review_notes`.
- Valida con:

```powershell
python scripts/validate_mapping_review.py reports/mapping_review_template.csv
python scripts/apply_mapping_review.py reports/mapping_review_template.csv --dry-run
```

Empieza por los temas `fallback` con mayor `unresolved_article_total` en `reports/mapping_status.md`, pero solo aprueba filas con fuente clara.
