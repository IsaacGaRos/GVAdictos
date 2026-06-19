# Fase 2E - Delimitacion fina PE-13

Autor: Codex
Fecha: 2026-06-18
Nivel de rigor: extremadamente alto
Estado: aplicado y validado

## Contexto

Claude Code completo la Fase 2D corrigiendo in-place Ley 40/2015 arts. 24-27. Tras esa correccion:

- `validate_article_quality.py` quedo en PASS.
- `topic_sources` quedo intacto.
- `article_id` de Ley 40/2015 se mantuvo estable.
- PE-13 quedo desbloqueado.

## Alcance aplicado

Tema:

- PE-13
- `topic_id = 28`
- Parte especial

Mapping aplicado con:

```text
validacion_articulos_claude_fase2e_pe13_2026_06_18
```

Rangos:

| Norma | law_id | Rango | Filas |
| --- | ---: | --- | ---: |
| Ley 40/2015 | 4 | arts. 1-53 | 54 |
| Ley 40/2015 | 4 | arts. 140-158 | 19 |
| Decreto 176/2014 | 27 | arts. 1-21 | 21 |

Total insertado: 94 filas en `topic_sources`.

Nota: Ley 40/2015 arts. 1-53 devuelve 54 filas porque la BD incluye el articulo 46 bis.

## Script

Script creado:

```powershell
python scripts/apply_fase2e_pe13_delimitation.py
python scripts/apply_fase2e_pe13_delimitation.py --apply
```

El script:

- es dry-run por defecto;
- crea backup antes de escritura real;
- valida `topic_id`, `law_id`, rangos y FKs;
- aborta si PE-13 ya tiene mapping fino ajeno;
- borra solo sus propias filas por `mapping_basis`;
- no modifica `articles`;
- no toca parser/importer;
- no reimporta normas.

## Resultado

Aplicacion:

- Backup: `db/gvadicto.backup_pre2e_pe13_20260618_160805.sqlite`
- `topic_sources`: 1192 -> 1286
- `topic_sources.article_id IS NOT NULL`: 985 -> 1079
- FKs rotas: 0
- PE-13 filas propias: 94

Reports:

- `reports/apply_fase2e_pe13_delimitation_20260618_160657.md` (dry-run)
- `reports/apply_fase2e_pe13_delimitation_20260618_160805.md` (apply)
- `reports/mapping_status.md`
- `reports/mapping_status.json`

## Validacion posterior

```powershell
python scripts/validate_article_quality.py
python scripts/report_mapping_status.py
```

Resultado:

- `validate_article_quality.py`: PASS.
- `broken_article_links`: 0.
- `article_law_mismatches`: 0.
- Temas con mapping fino: 16.
- Temas en fallback: 59.
- Progreso mapping fino: 21.33%.
- Marcador "Plan Anual Normativo" en Ley 40/2015: 0.

## No tocado

- No se ha tocado parser.
- No se ha tocado importer.
- No se ha reimportado normativa.
- No se ha modificado contenido de `articles`.
- No se han borrado mappings ajenos.
- Los enlaces fallback originales de PE-13 se conservan.

## Siguiente paso recomendado

Continuar con otro tema de alta confianza y delimitacion por estructura oficial clara, o pasar a QA visual de PE-13 en la pestana Estudiar.

Antes de nuevas escrituras:

```powershell
python scripts/validate_article_quality.py
python scripts/report_mapping_status.py
```
