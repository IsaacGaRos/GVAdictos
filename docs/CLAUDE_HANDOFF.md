# Traspaso a Claude Code - GVAdicto

Fecha de traspaso: 2026-06-17

## 1. Resumen ejecutivo

GVAdicto es una app local-first para estudiar oposiciones GVA. El MVP usa Python, Streamlit y SQLite. Ahora mismo el foco real es A1-01 GVA 2025, con normativa oficial descargada, importada, trazada y vigilada.

El proyecto no esta terminado: la normativa esta obtenida localmente y la validacion juridica fina tema por tema esta iniciada, pero sigue pendiente cerrar hallazgos, validar articulos exactos y revisar preguntas.

Estado cuantitativo verificado:

- `laws`: 77.
- `articles`: 11989.
- `questions`: 20, todas con `requiere_revision = 1`.
- `attempts`: 0.
- `source_documents`: 156.
- `topics`: 75.
- `topic_sources`: 198.
- `topic_validation_findings`: 32 abiertos.
- `source_update_checks`: 200 aprox.
- Cobertura normativa A1 inicial: 26 referencias expresas cubiertas, 0 pendientes.
- Validacion fina: 39 enlaces desde cobertura expresa, 134 inferidos del temario oficial y 25 desde contraste auxiliar Autentica.

## 2. Objetivo de producto

Queremos una herramienta local para:

- Importar normativa oficial sin alterar originales.
- Segmentar articulos/bloques.
- Crear preguntas tipo test con fuente.
- Resolver tests y registrar errores.
- Identificar fallos recurrentes.
- Generar simulacros.
- Aplicar repeticion espaciada.
- Mantener normativa actualizada mediante vigilancia semanal.
- Usar material academico de Drive solo como apoyo, nunca como fuente juridica definitiva.

## 3. Reglas juridicas no negociables

- No inventar contenido juridico.
- Toda pregunta debe tener fuente explicita.
- Toda explicacion debe poder trazarse a norma, articulo o documento oficial.
- No afirmar que una norma esta vigente sin fuente oficial.
- No usar documentos de academia como autoridad juridica final.
- BOE consolidado y EUR-Lex consolidado son textos informativos/documentales.
- La validacion juridica humana sigue pendiente aunque la fuente este importada.
- Si se generan preguntas con IA, marcar `requiere_revision = 1`.

## 4. Estructura del proyecto

Raiz:

- `app.py`: UI Streamlit.
- `requirements.txt`: dependencias.
- `AGENTS.md`: reglas heredadas de Codex.
- `CLAUDE.md`: instrucciones para Claude Code.
- `db/gvadicto.sqlite`: base de datos local.
- `data/sources/leyes_originales`: originales oficiales descargados.
- `data/processed/official_sources`: textos procesados.
- `data/sources/convocatorias/A1-01_2025`: bases, correcciones y CSV de temario/cobertura.
- `data/sources/drive_inventory`: inventario de Drive.
- `docs`: documentacion de estado, auditoria y roadmap.
- `docs/STUDY_INTERFACE_SPEC.md`: especificacion de la futura interfaz de estudio, anotaciones, versionado y Pomodoro.

Codigo:

- `src/core/db.py`: schema SQLite y conexion.
- `src/core/paths.py`: rutas.
- `src/core/source_catalog.py`: catalogo de fuentes.
- `src/laws/importer.py`: importacion de normas y parser de articulos.
- `src/tests/repository.py`: CRUD de preguntas.
- `src/mistakes/repository.py`: intentos y fallos.
- `src/reports/basic.py`: contadores.
- `src/core/export.py`: exportaciones CSV/Anki.

Scripts:

- `scripts/import_law.py`: importar TXT/MD manual.
- `scripts/import_source_manifest.py`: cargar manifiestos CSV en `source_documents`.
- `scripts/import_boe_pdf_laws.py`: importador historico de BOE PDF.
- `scripts/build_extra_sources_manifest.py`: descarga fuentes oficiales extra BOE/DOGV.
- `scripts/build_a1_topic_validation_sources_manifest.py`: descarga fuentes oficiales implicitas para validacion fina A1.
- `scripts/build_a1_autentica_supplemental_sources_manifest.py`: descarga fuentes oficiales detectadas por contraste auxiliar Autentica.
- `scripts/import_official_sources.py`: convierte PDF/HTML y llama al importador.
- `scripts/import_topics_and_validate_coverage.py`: importa 75 temas, enlaza fuentes y genera auditoria tema-fuente.
- `scripts/generate_controlled_questions.py`: genera lote piloto controlado, limpia entradas de indice del PDF, prefiere bloques de articulo con texto real y marca siempre `requiere_revision=1`.
- `scripts/check_source_updates.py`: hash/update de fuentes BOE/DOGV.
- `scripts/check_eurlex_versions.py`: vigilancia EUR-Lex por SPARQL y XHTML.
- `scripts/export_anki.py`: exportacion basica.
- `scripts/backup.py`: backup.

## 5. Base de datos

SQLite en `db/gvadicto.sqlite`.

Tablas principales:

- `laws`: normas/textos importados, hash, ruta, estado de validacion.
- `articles`: articulos/bloques segmentados, fuente, hash original.
- `questions`: preguntas tipo test.
- `attempts`: intentos del usuario.
- `source_documents`: catalogo de fuentes externas/oficiales.
- `source_update_checks`: comprobaciones de cambios por hash.
- `topics`: temario oficial A1-01 2025.
- `topic_sources`: enlaces tema -> norma/articulo con base de mapeo.
- `topic_validation_findings`: hallazgos abiertos de validacion juridica.

Todas las normas y articulos importados quedan por defecto con `validation_status = pendiente_de_validacion`.

## 6. Normativa A1 importada

Fuentes oficiales importadas:

- Textos normativos en SQLite: 77.
- BOE/DOGV/EUR-Lex catalogados en `source_documents`.

Incluye, entre otras:

- Constitucion Espanola.
- Ley 39/2015.
- Ley 40/2015.
- TREBEP.
- Ley 7/1985.
- LO 3/2007.
- LO 1/2004.
- Estatuto de los Trabajadores.
- LO 2/2012.
- Ley 38/2003.
- RD 203/2021.
- LCSP.
- Ley 1/2015 Generalitat.
- Ley 4/2021 Funcion Publica Valenciana.
- Ley 4/2023 Trans/LGTBI.
- Ley 5/1983 Consell.
- Ley 6/2024 Simplificacion Administrativa.
- Ley 8/2010 Regimen Local CV.
- Ley 9/2003 Igualdad mujeres/hombres.
- Ley 14/2003 Patrimonio Generalitat.
- Ley 20/2017 Tasas.
- Ley 6/2025 Presupuestos Generalitat 2025.
- Decreto 204/2025 prorroga presupuestaria 2026.
- Decreto 103/2014 precios publicos.
- Decreto 128/2017 ayudas publicas.
- Decreto 176/2014 convenios.
- Decreto 41/2016 calidad servicios.
- Decreto 54/2025 simplificacion y transformacion digital.
- Decreto-ley 14/2025.
- TUE `02016M/TXT-20250315`.
- TFUE `02016E/TXT-20250315`.

Tambien se incorporaron fuentes implicitas o detectadas por Autentica: Estatuto CV, LOREG, Ley Electoral Valenciana, leyes de instituciones estatutarias, LJCA, LOTC, LO 2/1987 conflictos jurisdiccionales, Ley 33/2003 patrimonio AAPP, LGSS, LOFCA, Ley 22/2009, Ley 13/1997, Ley 22/2001, RD 635/2014, Ley 25/2018, Ley 8/2016, Reglamento de Les Corts, decretos 3/2017, 42/2019, 49/2021, Decreto 25/2017, Orden 18/2023 NEFIS y Orden 27/12/2001 de clasificacion economica, entre otras.

Matrices y auditorias:

`data/sources/convocatorias/A1-01_2025/a1_01_2025_cobertura_normativa.csv`

`data/sources/convocatorias/A1-01_2025/a1_01_2025_topic_validation_audit.csv`

`data/sources/convocatorias/A1-01_2025/autentica_auxiliary_normative_indications.md`

## 7. Google Drive y material academico

El usuario aviso que `Archivo Oposicion TAG-GVA` puede estar desactualizado.

Drive revisado:

- `Mi Unidad -> Opo`.
- Carpetas principales: `Autentica` y `EraCEF`.
- Se catalogaron 75 PDFs desde `Opo/EraCEF/TemarioAulaVirtualCompleto`.
- Se uso `Opo/Autentica/Legislacion A1 2025 v4.pdf` como contraste auxiliar de cobertura normativa.
- El manifiesto local es `data/sources/drive_inventory/opo_temario_aula_virtual_2026.csv`.

Importante:

- Drive es apoyo academico, no fuente oficial.
- No importar material academico como normativa vigente.
- Si se usa para priorizar articulos/preguntas, contrastar con BOE/DOGV/EUR-Lex.
- Los mapeos de Autentica quedan con `mapping_basis = autentica_auxiliar_pendiente_validacion`.

## 8. Vigilancia normativa

La vigilancia debe ejecutarse en secuencia para evitar bloqueos SQLite:

```powershell
python scripts/check_source_updates.py --source-kind boe_consolidado --update-files
python scripts/check_source_updates.py --source-kind boe_pdf --update-files
python scripts/check_source_updates.py --source-kind dogv_pdf --update-files
python scripts/check_eurlex_versions.py --update-files --import-updated
```

No ejecutar en paralelo.

No ejecutar `check_source_updates.py --source-kind eurlex_html`; ese script generico no pone las cabeceras adecuadas para XHTML EUR-Lex. EUR-Lex debe ir por `check_eurlex_versions.py`.

En Codex habia una automatizacion semanal llamada `GVAdicto vigilancia normativa semanal`, configurada como seguimiento en el mismo chat. Si se migra completamente a Claude Code, esa automatizacion de Codex no se transfiere automaticamente. Habra que recrearla con una tarea programada, cron, Task Scheduler o un flujo propio de Claude si se quiere mantener.

## 9. Comandos de verificacion

Compilar:

```powershell
python -m compileall app.py src scripts
```

Conteo rapido:

```powershell
python - <<'PY'
from src.core.db import connect
with connect() as conn:
    for table in ["laws", "articles", "questions", "attempts", "source_documents", "source_update_checks"]:
        print(table, conn.execute(f"select count(*) from {table}").fetchone()[0])
PY
```

En PowerShell sin heredoc Unix:

```powershell
@'
from src.core.db import connect
with connect() as conn:
    for table in ["laws", "articles", "questions", "attempts", "source_documents", "source_update_checks"]:
        print(table, conn.execute(f"select count(*) from {table}").fetchone()[0])
'@ | python -
```

Ejecutar app:

```powershell
streamlit run app.py
```

## 10. Problemas conocidos

- El parser de articulos es simple; para algunos PDFs/EUR-Lex genera muchos bloques por protocolos, anexos o indices.
- TUE/TFUE importan tambien protocolos/declaraciones asociados del XHTML consolidado.
- Algunos textos consolidados son instrumentos documentales, no versiones juridicas autenticas.
- Hay 20 preguntas piloto desde Ley 39/2015; el generador evita entradas de indice, pero no son definitivas y requieren revision juridica.
- EUR-Lex pendiente: Carta de Derechos Fundamentales UE, RGPD y Reglamento UE/Euratom 2024/2509 no se importaron automaticamente con el descargador simple.
- No hay tests automatizados formales.
- La UI es MVP; no hay sistema avanzado de simulacros ni repeticion espaciada.
- La automatizacion de Codex no migra automaticamente a Claude.
- SQLite puede bloquearse si se ejecutan watchers en paralelo.

## 11. Siguiente trabajo recomendado

Orden recomendado:

1. Resolver los 32 hallazgos abiertos de `topic_validation_findings`.
2. Ajustar importacion EUR-Lex para Carta UE, RGPD y Reglamento UE/Euratom 2024/2509.
3. Marcar articulos/bloques clave por tema.
4. Crear una tabla o CSV de mapeo `tema -> norma -> articulos prioritarios`.
5. Revisar las 20 preguntas piloto y generar nuevos lotes solo sobre temas validados.
6. Construir simulacros configurables.
7. Implementar repeticion espaciada por fallos y dificultad.
8. Mejorar dashboard de progreso.

Nuevo objetivo de producto indicado por el usuario:

- Crear una interfaz de estudio completa dentro de la app.
- Mostrar todos los temas ordenados y separados en parte general / parte especifica.
- Al entrar en cada tema, mostrar que normativa entra y prepararla para estudiar.
- Permitir subrayados, notas, dudas, etiquetas y ediciones tipicas de opositor.
- Mantener esas anotaciones aunque se actualice la normativa si el contenido no cambia.
- Si el contenido cambia, permitir comparar version anterior y nueva conservando el trabajo previo.
- Incluir Pomodoro personalizable en la interfaz de estudio.

La especificacion detallada esta en `docs/STUDY_INTERFACE_SPEC.md`.

Nivel de inteligencia recomendado:

- Validacion juridica: extremadamente alto.
- Generacion inicial de preguntas tras validacion: alto.
- UI, filtros, exportaciones, simulacros: medio/alto.

## 12. Como debe trabajar Claude

Antes de cambiar codigo:

- Leer `CLAUDE.md`.
- Leer este documento.
- Revisar `docs/A1_LEGISLATION_AUDIT.md`.
- Ejecutar conteos de DB si va a tocar datos.
- Proponer alcance minimo y verificacion.

Al terminar:

- Listar archivos tocados.
- Indicar comandos ejecutados.
- Indicar riesgos juridicos.
- Indicar siguiente paso y nivel de rigor recomendado.
