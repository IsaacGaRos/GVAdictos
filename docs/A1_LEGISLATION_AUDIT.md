# Auditoria A1-01 GVA 2025

> Nota 2026-06-18: los recuentos de articulos de este informe son historicos. Para el estado operativo actual usar `docs/CURRENT_STATUS.md` y `docs/CLAUDE_HANDOFF.md`.

Fecha de trabajo: 2026-05-29
Actualizacion EUR-Lex: 2026-06-17

## Fuente oficial de bases

- Convocatoria 1/25, proceso selectivo 1, A1-01, turno libre.
- Bases: Orden 18/2025, de 9 de junio, publicada en DOGV 10129 de 2025-06-12.
- Correccion de errores del temario: DOGV 10164 de 2025-08-01.
- Nota informativa sobre temario: GVA, 2025-12.

Archivos descargados:

- `data/sources/convocatorias/A1-01_2025/DOGV_2025_21290_Orden_18_2025_A1-01_bases.pdf`
- `data/sources/convocatorias/A1-01_2025/DOGV_2025_30507_correccion_temario_A1-01.pdf`
- `data/sources/convocatorias/A1-01_2025/GVA_nota_informativa_temario_A1-01_2025.pdf`

## Temario extraido

- Temario oficial extraido: `data/sources/convocatorias/A1-01_2025/a1_01_2025_temario_oficial_extraido.csv`
- Total extraido: 75 temas.
  - Parte general: 15 temas.
  - Parte especial proceso selectivo 1: 60 temas.
- Normativa detectada por extraccion automatica: `data/sources/convocatorias/A1-01_2025/a1_01_2025_normativa_requerida_extraida.csv`
- Cobertura inicial: `data/sources/convocatorias/A1-01_2025/a1_01_2025_cobertura_normativa.csv`

## Estado local actual

- Leyes/textos normativos importados en SQLite: 80.
- Articulos/bloques importados: 12838.
- Fuentes de temario de Drive catalogadas: 75.
- Fuentes oficiales y auxiliares catalogadas: 156.
  - BOE consolidado: 60.
  - BOE diario: 1.
  - DOGV PDF: 10.
  - DOGV HTML: 4.
  - EUR-Lex/Publication Office XHTML: 5 catalogadas, 2 descargadas correctamente y 3 pendientes por error de descarga.
  - Google Drive academico catalogado: 75.
  - Autentica auxiliar catalogada: 1.

## Normativa estatal obtenida e importada

Se han descargado desde BOE consolidado, convertido a texto procesado e importado:

- Constitucion Espanola 1978.
- Ley 39/2015, procedimiento administrativo comun.
- Ley 40/2015, regimen juridico del sector publico.
- Real Decreto Legislativo 5/2015, TREBEP.
- Ley 7/1985, bases del regimen local.
- Ley Organica 3/2007, igualdad efectiva.
- Ley Organica 1/2004, violencia de genero.
- Real Decreto Legislativo 2/2015, Estatuto de los Trabajadores.
- Ley Organica 2/2012, estabilidad presupuestaria.
- Ley 38/2003, general de subvenciones.
- Real Decreto 203/2021, sector publico electronico.
- Ley 9/2017, contratos del sector publico.

Importacion:

```powershell
python scripts/import_boe_pdf_laws.py
```

## Normativa adicional obtenida e importada

Se han descargado y catalogado en `data/sources/official_normative_sources_extra.csv`:

- Ley 1/2015, hacienda publica, sector publico instrumental y subvenciones.
- Ley 4/2021, funcion publica valenciana.
- Ley 4/2023, igualdad real y efectiva de las personas trans y garantia de derechos LGTBI.
- Ley 5/1983, Gobierno Valenciano / Consell.
- Ley 6/2024, simplificacion administrativa.
- Ley 8/2010, regimen local de la Comunitat Valenciana.
- Ley 9/2003, igualdad entre mujeres y hombres.
- Ley 14/2003, patrimonio de la Generalitat Valenciana.
- Ley 20/2017, tasas.
- Ley 6/2025, presupuestos de la Generalitat para 2025.
- Decreto 204/2025, prorroga automatica de presupuestos 2025 para 2026.
- Decreto 103/2014, precios publicos.
- Decreto 128/2017, ayudas publicas.
- Decreto 176/2014, convenios de la Generalitat, DOGV consolidado.
- Decreto 41/2016, calidad de los servicios publicos y cartas de servicios, DOGV consolidado.
- Decreto 54/2025, simplificacion administrativa y transformacion digital.
- Decreto-ley 14/2025, hiperregulacion, agilizacion de procedimientos y unidad de mercado.

Importacion:

```powershell
python scripts/build_extra_sources_manifest.py
python scripts/import_source_manifest.py data/sources/official_normative_sources_extra.csv
python scripts/import_official_sources.py
```

Nota: se corrigio una descarga erronea inicial de Decreto 103/2014. El identificador DOGV correcto es `2014/6339`; `2014/6342` era una resolucion ajena y fue eliminado de SQLite.

## Cobertura normativa A1

Archivo: `data/sources/convocatorias/A1-01_2025/a1_01_2025_cobertura_normativa.csv`.

Resumen tras importacion:

- 26 referencias normativas cubiertas por BOE/DOGV/EUR-Lex local.
- 0 referencias pendientes de obtencion local en la matriz automatica.

La referencia a presupuestos se cubre con Ley 6/2025 y Decreto 204/2025 de prorroga, porque a fecha de trabajo 2026-05-29 no consta ley valenciana de presupuestos 2026 aprobada y publicada.

La referencia a Tratados constitutivos se cubre con:

- Tratado de la Union Europea, version consolidada EUR-Lex `02016M/TXT-20250315`.
- Tratado de Funcionamiento de la Union Europea, version consolidada EUR-Lex `02016E/TXT-20250315`.

Ambos se han descargado como XHTML oficial desde `publications.europa.eu/resource/celex/...SPA.xhtml`.

## Validacion fina tema por tema

Fecha de trabajo: 2026-06-17.

Se ha creado una capa de validacion tema-fuente en SQLite:

- `topics`: 75 temas oficiales A1-01 2025.
- `topic_sources`: 204 enlaces tema-fuente.
  - 39 desde referencias expresas de la cobertura oficial extraida.
  - 134 inferidos desde el enunciado oficial del temario.
  - 31 desde contraste auxiliar con Autentica, marcados como `autentica_auxiliar_pendiente_validacion`.
- `topic_validation_findings`: 32 hallazgos totales, 23 abiertos y 9 resueltos.
- Auditoria CSV: `data/sources/convocatorias/A1-01_2025/a1_01_2025_topic_validation_audit.csv`.
- Indicaciones auxiliares Autentica resumidas en: `data/sources/convocatorias/A1-01_2025/autentica_auxiliary_normative_indications.md`.

La fuente auxiliar de Autentica usada ha sido `Opo/Autentica/Legislacion A1 2025 v4.pdf` en Google Drive. Se ha catalogado como `auxiliar_no_oficial`; no debe usarse como fuente juridica final.

El usuario indica que Autentica obtuvo el 75% de las plazas de la convocatoria pasada. Debe usarse como senal auxiliar fuerte para priorizar estudio y revisar cobertura, sin sustituir fuentes oficiales.

## Normativa adicional detectada por validacion fina

Se han obtenido e importado fuentes oficiales adicionales para cubrir normas implicitas o senaladas por Autentica:

- Ley 50/1997, Gobierno.
- Ley Organica 6/1985, Poder Judicial.
- Ley Organica 2/1979, Tribunal Constitucional.
- Ley Organica 3/1981, Defensor del Pueblo.
- Ley Organica 2/1982, Tribunal de Cuentas.
- Ley 7/1988, Funcionamiento del Tribunal de Cuentas.
- Ley Organica 5/1982, Estatuto de Autonomia de la Comunitat Valenciana.
- Ley Organica 5/1985, Regimen Electoral General.
- Ley 1/1987, Electoral Valenciana.
- Ley 2/2021, Sindic de Greuges.
- Ley 6/1985, Sindicatura de Cuentas.
- Ley 10/1994, Consell Juridic Consultiu.
- Ley 12/1985, Consell Valencia de Cultura.
- Ley 7/1998, Academia Valenciana de la Llengua.
- Ley 1/2014, Comite Economic i Social.
- Ley 29/1998, Jurisdiccion Contencioso-administrativa.
- Ley de Expropiacion Forzosa de 1954 y su Reglamento de 1957.
- Real Decreto Legislativo 8/2015, Ley General de la Seguridad Social.
- Ley 47/2003, General Presupuestaria.
- Ley 19/2013 y Ley 1/2022, transparencia.
- Ley 4/2023, participacion ciudadana CV.
- Ley Organica 3/2018, proteccion de datos.
- Ley 2/2023, proteccion de informantes.
- Ley 53/1984, incompatibilidades.
- Ley 31/1995, prevencion de riesgos laborales.
- LOFCA 8/1980 y Ley 22/2009, financiacion autonomica.
- Ley 3/2019 y Ley 26/2018, servicios sociales e infancia CV.
- Ley Organica 2/1987, conflictos jurisdiccionales.
- Ley 33/2003, patrimonio de las administraciones publicas.
- Real Decreto 33/1986, regimen disciplinario.
- Ley 13/1997, tributos cedidos CV.
- Ley 22/2001, fondos de compensacion interterritorial.
- Real Decreto 635/2014, periodo medio de pago a proveedores.
- Ley 25/2018, grupos de interes CV.
- Ley 8/2016, conflictos de intereses CV.
- Reglamento de Les Corts.
- Decreto 3/2017, Decreto 42/2019, Decreto 49/2021.
- Decreto 25/2017, Orden 18/2023 NEFIS y Orden de 27 de diciembre de 2001 sobre clasificacion economica.

Estado tras importacion:

- Textos normativos importados en SQLite: 80.
- Articulos/bloques importados: 12838.
- Fuentes catalogadas: 156.
- Preguntas generadas: 20, todas `requiere_revision=1`.

Claude importo posteriormente Carta de Derechos Fundamentales de la Union Europea, Reglamento UE 2016/679 RGPD y Reglamento UE/Euratom 2024/2509. Queda pendiente validar articulado exacto por tema antes de generar nuevas preguntas.

## Generacion controlada de preguntas

Se ha creado el script `scripts/generate_controlled_questions.py`.

Primer lote piloto:

- 20 preguntas generadas desde Ley 39/2015.
- Temas: PE-09 a PE-12.
- Todas con `law_id`, `article_id`, `fuente` y etiqueta `generado_controlado_a1_v1`.
- Todas quedan con `requiere_revision=1`.
- El generador excluye entradas de indice con lideres de puntos y prefiere el bloque de articulo con mayor texto juridico real.
- No se han generado preguntas desde fuentes auxiliares de academia.
- El lote sigue siendo piloto tecnico; no debe ampliarse hasta cerrar la validacion de articulado exacto por tema.

## Vigilancia semanal

Implementado:

```powershell
python scripts/check_source_updates.py --source-kind boe_consolidado --update-files
python scripts/check_source_updates.py --source-kind boe_pdf --update-files
python scripts/check_source_updates.py --source-kind dogv_pdf --update-files
python scripts/check_eurlex_versions.py --update-files --import-updated
```

El script:

- Descarga/comprueba fuentes catalogadas.
- Calcula hash SHA-256.
- Registra cada comprobacion en `source_update_checks`.
- Si cambia una fuente oficial BOE/DOGV no Google y se usa `--update-files`, actualiza la copia local.
- Para EUR-Lex se usa `check_eurlex_versions.py`, que consulta SPARQL de Cellar/Publications Office para detectar la ultima version consolidada y descargar el XHTML oficial en castellano.

Automatizacion creada:

- `GVAdictos vigilancia normativa semanal`
- Frecuencia: lunes a las 08:00.
- Alcance actual: fuentes `boe_consolidado`, `boe_pdf`, `dogv_pdf` y versiones consolidadas EUR-Lex de TUE/TFUE.

Comprobacion inicial:

- BOE consolidado: 21 comprobadas, 0 cambios, 0 errores.
- BOE diario: 1 comprobada, 0 cambios, 0 errores.
- DOGV: 7 comprobadas, 0 cambios, 0 errores.
- EUR-Lex TUE/TFUE: 2 comprobadas, version vigente detectada `2025-03-15`, 0 cambios, 0 errores.

## Limites

- Los textos consolidados BOE son utiles para estudiar, pero el propio BOE advierte que tienen caracter informativo y no valor juridico.
- La afirmacion definitiva de que una norma entra o esta vigente debe contrastarse con bases oficiales, correcciones y texto oficial aplicable en la fecha del ejercicio.
- La normativa autonomica importada desde DOGV/BOE queda como `pendiente_de_validacion`.
- Los textos EUR-Lex consolidados son instrumentos de documentacion y se mantienen como `pendiente_de_validacion`; las versiones autenticas son las publicadas en el Diario Oficial de la Union Europea.
