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
- 77 textos normativos oficiales descargados, procesados e importados.
- 75 temas oficiales A1-01 2025 importados en SQLite.
- 198 enlaces tema-fuente para validacion fina.
- 20 preguntas piloto generadas desde Ley 39/2015, todas con fuente y `requiere_revision=1`.
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
- Autentica se ha usado como contraste auxiliar desde Drive, no como fuente juridica oficial.
- Vigilancia semanal creada para fuentes BOE consolidadas, BOE diario, DOGV y EUR-Lex TUE/TFUE.

## Pendiente

- Resolver 32 hallazgos abiertos de validacion fina.
- Ajustar importacion EUR-Lex para Carta de Derechos Fundamentales UE, RGPD y Reglamento UE/Euratom 2024/2509.
- Validar articulado exacto por tema antes de ampliar preguntas.
- Revisar juridicamente el lote piloto antes de usarlo como banco de estudio definitivo.
- Simulacros configurables.
- Repeticion espaciada completa.
- Planificador.
- Integraciones externas.
- Validacion juridica humana de normativa vigente y bases de convocatoria.
