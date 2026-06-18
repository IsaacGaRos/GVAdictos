# Resumen de sesion Codex

Se implemento la Fase 1 MVP solicitada en la especificacion inicial.

Decisiones:

- Stack Python + Streamlit + SQLite.
- Persistencia local en `db/gvadicto.sqlite`.
- Originales guardados en `data/sources/leyes_originales`.
- Contenido importado marcado como `pendiente_de_validacion`.
- Sin Google Calendar, LifeHub ni planificacion adaptativa.

Nota posterior:

- El usuario indico que `Archivo Oposicion TAG-GVA` puede estar desactualizado.
- Para materiales actualizados, revisar Google Drive en `Mi Unidad -> Opo` cuando proceda.

Avance de catalogacion:

- Localizada en Drive la carpeta `Opo/EraCEF/TemarioAulaVirtualCompleto`.
- Catalogados 60 PDFs de temario 2026 en `data/sources/drive_inventory/opo_temario_aula_virtual_2026.csv`.
- Creada tabla SQLite `source_documents` para registrar fuentes externas.
- Cargado el manifiesto en `db/gvadicto.sqlite`.
- La validacion juridica de vigencia y bases queda pendiente.

Avance A1:

- Descargadas bases oficiales A1-01 2025, correccion de temario y nota informativa.
- Extraido el temario corregido: 75 temas.
- Corregido el catalogo de Drive a 75 PDFs.
- Descargadas/importadas 12 normas estatales BOE consolidadas.
- Implementado `scripts/check_source_updates.py`.
- Creada automatizacion semanal de vigilancia normativa.

Avance normativa faltante:

- Descargadas/importadas 17 fuentes oficiales adicionales desde BOE/DOGV.
- Importados TUE y TFUE desde XHTML oficial Publications Office/EUR-Lex.
- Total actual tras avances posteriores de Claude: 80 textos normativos oficiales y 12838 articulos/bloques en SQLite.
- Regenerada `data/sources/convocatorias/A1-01_2025/a1_01_2025_cobertura_normativa.csv`.
- `Tratados constitutivos` queda cubierto por TUE `02016M/TXT-20250315` y TFUE `02016E/TXT-20250315`.
- Implementado `scripts/check_eurlex_versions.py` para detectar por SPARQL la ultima version consolidada de TUE/TFUE.
- La vigilancia semanal ahora cubre `boe_consolidado`, `boe_pdf`, `dogv_pdf` y EUR-Lex TUE/TFUE.

Avance validacion fina A1:

- Importados 75 temas oficiales en `topics`.
- Creados 204 enlaces tema-fuente en `topic_sources`.
- Registrados 32 hallazgos totales en `topic_validation_findings`: 23 abiertos y 9 resueltos.
- Usado `Opo/Autentica/Legislacion A1 2025 v4.pdf` como contraste auxiliar no oficial.
- Generadas 20 preguntas piloto desde Ley 39/2015, todas `requiere_revision=1`.
- Claude importo Carta UE, RGPD y Reglamento UE/Euratom 2024/2509; queda pendiente validacion de articulado exacto y revision juridica fina.
- Claude implemento la pestaña `Estudiar` como navegador inicial de temas; el siguiente corte recomendado es anotacion minima persistente.
