# Mapping workflow A1-01 GVA

Este flujo prepara la delimitacion fina tema -> norma -> articulo sin hacer trabajo juridico automatico.
Las herramientas son tecnicas: auditan, generan plantilla, validan y preparan una aplicacion futura.

## Principios

- No modificar `data/sources/leyes_originales`.
- No reimportar normas para esta fase.
- No tocar `articles`.
- No modificar `db/gvadicto.sqlite` salvo ejecucion futura y explicita de `scripts/apply_mapping_review.py --apply`.
- No inventar articulos ni rangos genericos.
- Todo mapping juridico debe venir de revision con fuente, preferentemente Autentica + fuente oficial cuando toque.
- Los mappings protegidos con `mapping_basis = validacion_articulos_codex_2026_06_18` no deben sobrescribirse.

## 1. Auditar estado actual

```powershell
python scripts/report_mapping_status.py
python scripts/audit_fallback_topics.py
python scripts/audit_existing_fine_mappings.py
```

Salidas:

- `reports/mapping_status.md`
- `reports/mapping_status.json`
- `reports/fallback_topics.md`
- `reports/fallback_topics.csv`
- `reports/existing_fine_mappings.md`
- `reports/existing_fine_mappings.csv`

`fallback_topics.csv` lista grupos tema-norma, articulos totales de cada norma, articulos ya vinculados si existen y estado tecnico:

- `mapped`: la norma del tema ya tiene articulos concretos.
- `partial`: el tema mezcla normas con y sin articulos concretos.
- `fallback`: el tema no tiene articulos concretos.
- `ambiguous`: hay inconsistencia tecnica que exige revision.

## 2. Generar plantilla de revision

```powershell
python scripts/generate_mapping_review_template.py
```

Salida:

- `reports/mapping_review_template.csv`

Columnas principales:

- `part`
- `topic_number`
- `topic_title`
- `law_id`
- `law_title`
- `current_status`
- `candidate_article_refs`
- `autentica_reference`
- `confidence`
- `review_notes`
- `approved`
- `article_ids_to_apply`

Columnas tecnicas anadidas:

- `topic_id`
- `normative_reference`
- `candidate_article_count`
- `current_linked_article_ids`
- `mapping_basis`

`candidate_article_refs` contiene candidatos tecnicos sacados de la tabla `articles`.
No son delimitacion juridica aprobada.

## 3. Revisar con Autentica

Para cada fila pendiente:

1. Abrir el tema en Autentica/CEF/oficial si procede.
2. Identificar articulos exactos que entran.
3. Rellenar `autentica_reference` con referencia util al material usado.
4. Rellenar `review_notes` con criterio de delimitacion.
5. Rellenar `confidence`.
6. Marcar `approved = 1` solo si esta revisado.
7. Rellenar `article_ids_to_apply` con ids explicitos separados por `;`.

No usar rangos tipo `100-120` en `article_ids_to_apply`.
Si entran varios articulos, escribir todos los `article_id` concretos.

## 4. Validar plantilla revisada

```powershell
python scripts/validate_mapping_review.py reports/mapping_review_template.csv
```

El validador comprueba:

- Los `article_id` existen.
- Los `article_id` pertenecen a la `law_id` de la fila.
- La ley esta asociada al tema.
- No hay filas aprobadas sin articulos.
- No hay filas aprobadas sin `autentica_reference` ni `review_notes`.
- No se duplican mappings existentes.
- No se intenta sobrescribir mappings protegidos.
- Los mappings protegidos actuales siguen resolviendo a articulos validos.

No escribe en la BD.

## 5. Dry-run de aplicacion

```powershell
python scripts/apply_mapping_review.py reports/mapping_review_template.csv --dry-run
```

Tambien es dry-run si no se pasa `--apply`.

El dry-run:

- valida la plantilla,
- genera informe before/after,
- lista mappings planificados,
- no escribe en `db/gvadicto.sqlite`.

Salida:

- `reports/apply_mapping_review_<timestamp>.md`
- `reports/apply_mapping_review_<timestamp>.json`

## 6. Aplicacion futura

Solo cuando la plantilla este revisada:

```powershell
python scripts/apply_mapping_review.py reports/mapping_review_template.csv --apply
```

Antes de insertar crea backup automatico en:

```text
db/backups/
```

La aplicacion:

- no toca `articles`,
- no reimporta normas,
- no borra mappings existentes,
- no borra mappings protegidos Codex,
- inserta nuevas filas `topic_sources` con `article_id`,
- registra `mapping_basis`.

## 7. Revertir

Si una aplicacion futura sale mal:

1. Cerrar la app si esta usando la BD.
2. Copiar el backup desde `db/backups/`.
3. Sustituir manualmente `db/gvadicto.sqlite` por el backup correcto.
4. Regenerar:

```powershell
python scripts/report_mapping_status.py
python scripts/audit_existing_fine_mappings.py
```

## 8. Checks tecnicos

```powershell
python scripts/test_mapping_tools.py
python -m compileall scripts
```

Los checks cubren:

- modo read-only/dry-run sin cambio de hash de la BD,
- `article_id` inexistente,
- `article_id` de otra norma,
- tema aprobado sin articulos,
- intento de sobrescribir mapping protegido.

## 9. Uso recomendado con Claude/Opus

1. Ejecutar auditorias.
2. Abrir `reports/fallback_topics.csv` para priorizar.
3. Abrir `reports/mapping_review_template.csv`.
4. Rellenar solo filas revisadas juridicamente.
5. Validar con `scripts/validate_mapping_review.py`.
6. Ejecutar dry-run con `scripts/apply_mapping_review.py --dry-run`.
7. Aplicar solo cuando el usuario lo autorice.

El foco de Claude/Opus debe ser juridico: decidir articulos exactos con fuente.
El foco de estas herramientas es tecnico: hacer que esa decision sea verificable y reversible.
