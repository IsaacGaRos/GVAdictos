# Estado actual

Fase 1 MVP implementada en version inicial.

## Fuentes de materiales

- El directorio local `Archivo Oposicion TAG-GVA` puede estar desactualizado.
- El usuario indica que puede haber archivos mas actualizados en Google Drive: `Mi Unidad -> Opo`.
- Se ha inspeccionado Drive `Mi Unidad -> Opo` como inventario auxiliar; la importacion normativa se ha hecho desde fuentes oficiales BOE/DOGV/EUR-Lex.

## Disponible

- App Streamlit local.
- SQLite local.
- Catalogo de fuentes externas en SQLite (`source_documents`).
- 81 textos normativos oficiales descargados, procesados e importados.
- 6792 articulos normativos parseados tras normalizacion y deduplicacion.
- 75 temas oficiales A1-01 2025 importados en SQLite.
- 1286 enlaces tema-fuente/articulo en `topic_sources`.
- 1079 enlaces con `article_id` y 16 temas con mapping fino.
- 20 preguntas piloto generadas desde Ley 39/2015, todas con fuente y `requiere_revision=1`.
- PestaÃ±a `Estudiar` implementada en Streamlit como navegador inicial de temas A1-01.
- Anotacion minima persistente implementada en `study_annotations`: nota, subrayado, duda y marcador vinculables a tema y/o articulo.
- Importador TXT/MD.
- CRUD basico de preguntas.
- Modo test.
- Registro de intentos y fallos.
- Exportaciones CSV.

## Drive catalogado

- Cargadas 75 fuentes PDF desde `Opo/EraCEF/TemarioAulaVirtualCompleto`: 15 de parte general y 60 de parte especial.
- Manifiesto local: `data/sources/drive_inventory/opo_temario_aula_virtual_2026.csv`.
- Estado juridico de todas esas fuentes: `pendiente_de_validacion`.
- No se ha afirmado vigencia normativa ni correspondencia con bases oficiales.

## A1-01 2025

- Bases oficiales descargadas desde DOGV/GVA en `data/sources/convocatorias/A1-01_2025`.
- Temario oficial corregido extraido a CSV.
- Cobertura normativa inicial generada.
- Informe: `docs/A1_LEGISLATION_AUDIT.md`.
- Cobertura normativa A1 regenerada tras importar normativa autonomica pendiente.
- Validacion fina tema por tema iniciada y registrada en:
  - `data/sources/convocatorias/A1-01_2025/a1_01_2025_topic_validation_audit.csv`
  - tablas SQLite `topics`, `topic_sources`, `topic_validation_findings`
- Validacion de articulos exactos completada para los temas 8, 17, 18, 21, 32, 52, 54 y 55 en `.claude/VALIDACION_ARTICULOS_POR_TEMA.md`.
- Reglamento de Les Corts BOE 2026 importado desde BOE-A-2026-5880 como fuente oficial vigente para Tema 8. El DOGV consolidado 2024 queda como referencia historica/equivalencia, no como fuente principal para el mapeo.
- Mapeos por articulo aplicados en SQLite con `mapping_basis = validacion_articulos_codex_2026_06_18`.
- Recuento de mapeos aplicados: Tema 8 PG = 51 articulos; Tema 17 PE = 170 articulos unicos + 3 referencias sin articulo parseado; Tema 18 PE = 48; Tema 21 PE = 114; Tema 32 PE = 114 articulos; Tema 52 PE = 8; Tema 54 PE = 2; Tema 55 PE = 7.
- Fase 2E PE-13 aplicada con `mapping_basis = validacion_articulos_claude_fase2e_pe13_2026_06_18`: Ley 40/2015 arts. 1-53 y 140-158; Decreto 176/2014 arts. 1-21; 94 filas insertadas; FKs rotas 0.
- Autentica se ha usado como contraste auxiliar desde Drive, no como fuente juridica oficial.
- Autentica debe tratarse como senal academica auxiliar de alta prioridad: el usuario indica que obtuvo el 75% de las plazas en la convocatoria pasada. Prioriza, pero no sustituye BOE/DOGV/EUR-Lex.
- Claude importo directamente Carta UE, RGPD y Reglamento UE/Euratom 2024/2509 desde EUR-Lex; queda pendiente validacion de articulado exacto.
- Vigilancia semanal creada para fuentes BOE consolidadas, BOE diario, DOGV y EUR-Lex TUE/TFUE.

## Pendiente

- Resolver 21 hallazgos abiertos de validacion fina.
- Mejorar Estudiar con remapeo de anotaciones tras cambios normativos, comparacion de versiones, Pomodoro y accion contextual para preguntar dudas a IA.
- Revisar juridicamente el lote piloto antes de usarlo como banco de estudio definitivo.
- Simulacros configurables.
- Repeticion espaciada completa.
- Planificador.
- Integraciones externas.
- Validacion juridica humana de normativa vigente y bases de convocatoria.
