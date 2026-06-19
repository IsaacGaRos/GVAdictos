# Traspaso a Claude Code - GVAdictos

Fecha de traspaso: 2026-06-18
Responsable de esta actualizacion: Codex

## 1. Resumen ejecutivo

GVAdictos es una app local-first para estudiar la oposicion A1-01 GVA 2025. El MVP usa Python, Streamlit y SQLite. El foco actual no es C2: cualquier referencia principal a C2 debe tratarse como residuo antiguo salvo que el usuario pida limpiarla.

La normativa oficial A1 esta importada y catalogada. La validacion juridica fina esta en curso. Ya se completo y aplico a SQLite la delimitacion por articulos de los temas prioritarios 8, 17, 18, 21, 32, 52, 54 y 55.

Estado cuantitativo verificado el 2026-06-18:

- `laws`: 81.
- `articles`: 11509.
- `questions`: 20, todas con `requiere_revision = 1`.
- `attempts`: 0.
- `source_documents`: 157.
- `source_update_checks`: 206 aprox.
- `topics`: 75.
- `topic_sources`: 742.
- `topic_validation_findings`: 21 abiertos, 11 resueltos.

## 2. Reglas juridicas no negociables

- No inventar contenido juridico.
- Toda pregunta o explicacion debe tener fuente.
- No modificar originales oficiales en `data/sources/leyes_originales`.
- No usar documentos de academia como fuente juridica final.
- Autentica y CEF son apoyo academico y senal de prioridad, no autoridad normativa.
- El usuario indico que Autentica obtuvo el 75% de las plazas en la convocatoria pasada; por eso sus indicaciones pesan mucho para priorizar, pero siempre hay que contrastar con BOE, DOGV/GVA o EUR-Lex.
- Todo contenido juridico generado por IA debe quedar marcado como `requiere_revision = 1` si entra en tablas de preguntas/contenido generado.
- La validacion humana final sigue pendiente aunque Codex haya contrastado articulos con fuente oficial.

## 3. Estructura relevante

- `app.py`: UI Streamlit.
- `db/gvadicto.sqlite`: base local.
- `src/core/db.py`: esquema SQLite.
- `src/laws/importer.py`: parser/importador de normas.
- `src/core/source_catalog.py`: catalogo de fuentes.
- `src/studies/annotations.py`: CRUD de anotaciones de estudio.
- `scripts/import_official_sources.py`: convierte PDF/HTML y reimporta normas.
- `scripts/check_source_updates.py`: vigilancia generica BOE/DOGV por hash.
- `scripts/check_eurlex_versions.py`: vigilancia EUR-Lex; usar este para EUR-Lex, no el checker generico.
- `scripts/apply_a1_article_validation.py`: importa Reglamento Les Corts BOE 2026 y aplica mapeos articulo-tema validados.
- `scripts/reimport_with_deduplication.py`: reimportador de mantenimiento corregido para convertir PDF/HTML a TXT antes de llamar a `import_law`; no debe importar PDFs directamente.
- `.claude/VALIDACION_ARTICULOS_POR_TEMA.md`: documento juridico operativo con articulos exactos y justificacion oficial.
- `docs/STUDY_INTERFACE_SPEC.md`: especificacion de interfaz de estudio, anotaciones, versionado y Pomodoro.

## 4. Estado normativo A1

Fuentes oficiales principales ya importadas: Constitucion, Ley 39/2015, Ley 40/2015, TREBEP, LCSP, LGSS, Estatuto CV, Ley 5/1983, Ley 1/1987, Ley 14/2003, Ley 33/2003, TUE/TFUE, Carta UE, RGPD y Reglamento UE/Euratom 2024/2509, ademas de normativa autonomica y reglamentaria de apoyo.

Reglamento de Les Corts:

- Antes existia en BD el DOGV consolidado 2024.
- Codex importo el texto vigente BOE 2026 desde `BOE-A-2026-5880`.
- Nueva norma en `laws`: `Reglamento de Les Corts BOE 2026`.
- Fuente local: `data/sources/leyes_originales/BOE/BOE-A-2026-5880_Reglamento_Les_Corts_2026.html`.
- Texto procesado: `data/processed/official_sources/BOE-A-2026-5880.txt`.
- Tambien queda en `source_documents` como `source_kind = boe_html`, `external_id = BOE-A-2026-5880`.
- Hay hash base de vigilancia creado con `python scripts/check_source_updates.py --source-kind boe_html`.

Limitacion conocida: el parser actual no detecta bien todos los articulos ordinales iniciales del Reglamento 2026, pero no afecta al Tema 8 porque los arts. 112-139 si se parsean.

## 5. Mapeos aplicados

`scripts/apply_a1_article_validation.py` es idempotente: descarga/cataloga Reglamento 2026, solo lo reimporta si cambia el hash o faltan articulos, borra solo mapeos de su propio `mapping_basis` y reinserta filas. Esto evita regenerar `article_id` sin necesidad ahora que existen anotaciones persistentes.

`mapping_basis` aplicado:

```text
validacion_articulos_codex_2026_06_18
```

`validation_status` aplicado a esos mapeos:

```text
validado_fuente_oficial_pendiente_revision_humana
```

Recuento aplicado:

- Tema 8 PG: 51 articulos unicos.
- Tema 17 PE: 170 articulos unicos, 184 filas de mapeo, 3 referencias sin articulo parseado.
- Tema 18 PE: 48 articulos unicos.
- Tema 21 PE: 114 articulos unicos.
- Tema 32 PE: 114 articulos unicos.
- Tema 52 PE: 8 articulos unicos, 10 filas de mapeo.
- Tema 54 PE: 2 articulos unicos, 5 filas de mapeo.
- Tema 55 PE: 7 articulos unicos, 12 filas de mapeo.

Hallazgos cerrados por este trabajo:

- Tema 8: delimitacion Reglamento Les Corts.
- Tema 17: delimitacion patrimonio/Ley 33/2003.

Siguen abiertos los hallazgos sectoriales de temas 52/54/55 porque el Estatuto CV ya esta delimitado, pero falta matriz de normas sectoriales principales.

## 6. Cambios en la app de estudio

`app.py` ya tenia pestana `Estudiar`. Codex corrigio el comportamiento de carga de articulos:

- Si un tema tiene filas `topic_sources.article_id`, Estudio muestra solo esos articulos delimitados.
- Si no hay mapeo fino por articulo, conserva fallback por `law_id`.
- `load_topic_normativa` agrupa por norma y cuenta articulos unicos.
- Se corrigio un uso incorrecto de `sqlite3.Row.get`.

Esto era necesario porque, antes de la correccion, un tema con LCSP arts. 1-114 habria mostrado toda la ley en vez de los 114 articulos delimitados.

## 7. Vigilancia normativa

Ejecutar en secuencia, no en paralelo, para evitar bloqueos SQLite:

```powershell
python scripts/check_source_updates.py --source-kind boe_consolidado --update-files
python scripts/check_source_updates.py --source-kind boe_pdf --update-files
python scripts/check_source_updates.py --source-kind boe_html --update-files
python scripts/check_source_updates.py --source-kind dogv_pdf --update-files
python scripts/check_eurlex_versions.py --update-files --import-updated
```

No usar `check_source_updates.py --source-kind eurlex_html`; EUR-Lex necesita `check_eurlex_versions.py`.

Codex tenia configurada una vigilancia semanal en el mismo chat. Esa automatizacion no migra automaticamente a Claude Code; si se trabaja fuera de Codex hay que recrearla con Task Scheduler, cron o flujo equivalente.

## 8. Verificacion ya ejecutada

```powershell
python scripts/import_official_sources.py
python scripts/apply_a1_article_validation.py
python -m compileall app.py src scripts
python scripts/check_source_updates.py --source-kind boe_html
git diff --check
```

`git diff --check` no reporto errores de whitespace; solo avisos esperables LF/CRLF.

Tambien se probo CRUD real de `study_annotations` con creacion, actualizacion y borrado de una anotacion temporal. Streamlit responde en `http://localhost:8501` con estado HTTP 200. Queda pendiente una prueba visual humana navegando por la pestaña Estudiar.

## 9. Riesgos pendientes

- No hay tests automatizados formales.
- Hay 20 preguntas piloto de Ley 39/2015; no deben considerarse banco definitivo hasta revision juridica.
- El parser de articulos es simple y puede generar falsos positivos en PDFs complejos.
- En Ley 33/2003 hay 3 referencias de disposiciones (`DA 3`, `DT 1.1`, `DT 5`) sin `article_id` porque el importador no parsea disposiciones como articulos.
- Los temas 52/54/55 necesitan normas sectoriales ademas del Estatuto CV.
- Anotacion minima persistente ya implementada: tabla `study_annotations`, repositorio `src/studies/annotations.py` y CRUD en pestaÃ±a Estudiar.
- Falta remapeo avanzado de anotaciones tras cambios normativos y comparacion de versiones.

## 10. Siguiente trabajo recomendado

1. Probar `streamlit run app.py` y verificar visualmente la pestana Estudiar:
   - Tema general 8 debe mostrar Reglamento Les Corts BOE 2026 arts. 112-139 junto con Ley 5/1983 y Ley 1/1987 delimitadas.
   - Tema especial 21 debe mostrar 114 articulos LCSP delimitados, no toda la ley.
   - Tema especial 32 debe mostrar 114 articulos LGSS delimitados.
2. Mejorar la experiencia de anotaciones: filtros por tipo, contador por articulo y mejor flujo para seleccionar fragmentos.
3. Incorporar accion contextual futura: seleccionar fragmento y preguntar duda a IA, con modo mock/fallback y sin generar contenido juridico no trazado.
4. Revisar las 20 preguntas piloto y despues generar preguntas solo sobre articulos validados, siempre con fuente y `requiere_revision = 1`.
5. Continuar los 21 hallazgos abiertos de validacion fina, priorizando normas sectoriales de competencias y temas con indicaciones fuertes de Autentica.

## 11. Nivel recomendado

- Prueba visual Streamlit: medio.
- Mejoras simples de anotaciones: medio/alto.
- Remapeo robusto de anotaciones tras cambios normativos: extremadamente alto.
- Validacion juridica sectorial o generacion avanzada de preguntas: extremadamente alto para validar, alto para generar una vez validado.
