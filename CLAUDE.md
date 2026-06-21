# CLAUDE.md - GVAdictos

## Rol del asistente

Actua como ingeniero senior pragmatico y como asistente de estudio juridico con rigor documental. Este proyecto contiene normativa para oposiciones GVA; cualquier afirmacion juridica debe estar trazada a fuente.

## Objetivo del proyecto

GVAdictos es una app local-first para preparar oposiciones GVA. El foco actual es A1-01 GVA 2025.

El objetivo practico es:

- Mantener normativa oficial descargada, trazada y vigilada.
- Crear una base de articulos y preguntas tipo test siempre con fuente.
- Registrar fallos, causas de error y evolucion.
- Avanzar hacia simulacros, repeticion espaciada y planificacion adaptativa.

## Reglas criticas

- No inventar contenido juridico.
- Toda pregunta, explicacion, resumen o cambio normativo debe tener fuente.
- No modificar originales en `data/sources/leyes_originales`.
- Todo contenido importado queda como `pendiente_de_validacion` hasta revision humana.
- Los textos consolidados BOE/EUR-Lex son utiles para estudiar, pero tienen caracter informativo/documental.
- Las versiones autenticas son las publicadas oficialmente en BOE, DOGV o Diario Oficial de la Union Europea.
- No usar PDFs de academia o Drive como fuente juridica definitiva sin contrastar con fuente oficial.
- Autentica es una senal academica auxiliar de alta prioridad: el usuario indica que obtuvo el 75% de las plazas de la convocatoria pasada. Usarla para priorizar que estudiar y donde mirar, pero nunca como autoridad juridica final.
- El directorio local `Archivo Oposicion TAG-GVA` puede estar desactualizado.
- Para material academico mas actualizado, revisar Google Drive `Mi Unidad -> Opo`, pero solo como apoyo.
- Trabajar en cambios pequenos, verificables y documentados.
- No meter credenciales en el repo. Usar `.env` si aparece una integracion externa.

## Nivel de rigor

- Tareas normales de UI/scripts: nivel medio/alto.
- Validacion juridica, comparacion de bases o decision sobre vigencia normativa: nivel extremadamente alto.
- Generacion de preguntas juridicas: solo despues de validar fuente; marcar `requiere_revision = 1` si hay ayuda de IA.

## Estado actual resumido

- App Streamlit local: `app.py`.
- Base SQLite: `db/gvadicto.sqlite`.
- Textos normativos oficiales importados: 80.
- Articulos/bloques importados: 12838.
- Fuentes catalogadas: 156.
- Temas oficiales A1-01 2025 importados: 75.
- Enlaces tema-fuente de validacion fina: 204.
- Hallazgos abiertos de validacion fina: 23.
- Fuentes oficiales vigiladas: BOE consolidado, BOE diario, DOGV y EUR-Lex TUE/TFUE.
- Cobertura A1 normativa automatica: 26/26 referencias cubiertas localmente, 0 pendientes de obtencion.
- Preguntas actuales: 20 piloto desde Ley 39/2015, con fuente y todas `requiere_revision = 1`.
- Intentos actuales: 0.

## Foco actual de producto

> **AL EMPEZAR UN CHAT NUEVO, LEE PRIMERO `NEXT_CHAT_START_HERE.md`** (raiz del repo) y
> `CURRENT_BASELINE.md`, `RULES_DO_NOT_BREAK.md`, `MEMORY_COMPACT_DUMP.md`. Son la fuente
> de verdad del estado y del roadmap priorizado.

**Prioridad desde 2026-06-22: GVAdictos como plataforma DIARIA de estudio**, alineada con la
planificacion mensual de Academia Autentica (la enviara el usuario). No iniciar funcionalidades
grandes nuevas mientras lo necesario para el ritmo diario no este cerrado.

Hecho reciente: ranking de "lo mas preguntado" REHECHO solo con examenes oficiales GVA
(13 papers, 9 convocatorias A1-01 + C1-01, 1185 preguntas, 0 sin articulo). Pestaña
"🔥 Mas preguntado". Ver `docs/EXAM_RANKING_PIPELINE.md`.

Prioridad historica (ya consolidada): seccion `Estudio` creada por Claude.

Estado de `Estudio`:

- Ya existe una pestaña `Estudiar` en Streamlit para listar temas A1-01 por parte general/especifica.
- Ya permite abrir un tema, mostrar su enunciado oficial y mostrar normativa/articulos vinculados cuando existen relaciones usables.
- Siguiente corte: anotacion minima persistente.
- Incorporar como idea de producto: seleccionar un fragmento y, mediante click derecho o accion contextual equivalente, preguntar una duda a la IA. La respuesta debe guardar fuente/contexto y quedar marcada como `requiere_revision`.

## Comandos principales

Instalar:

```powershell
pip install -r requirements.txt
```

Ejecutar app:

```powershell
streamlit run app.py
```

Verificar proyecto:

```powershell
python -m compileall app.py src scripts
```

Importar manifiestos oficiales:

```powershell
python scripts/import_source_manifest.py data/sources/official_normative_sources_extra.csv
python scripts/import_source_manifest.py data/sources/official_normative_sources_a1_topic_validation.csv
python scripts/import_source_manifest.py data/sources/official_normative_sources_a1_autentica_supplemental.csv
python scripts/import_source_manifest.py data/sources/official_normative_sources_eurlex.csv
python scripts/import_official_sources.py
```

Validacion fina A1:

```powershell
python scripts/import_topics_and_validate_coverage.py
python scripts/generate_controlled_questions.py
```

Vigilancia normativa semanal, siempre en secuencia:

```powershell
python scripts/check_source_updates.py --source-kind boe_consolidado --update-files
python scripts/check_source_updates.py --source-kind boe_pdf --update-files
python scripts/check_source_updates.py --source-kind dogv_pdf --update-files
python scripts/check_eurlex_versions.py --update-files --import-updated
```

No ejecutes `check_source_updates.py` para `eurlex_html`; EUR-Lex se comprueba con `check_eurlex_versions.py`.

## Documentos de referencia

- `docs/CLAUDE_HANDOFF.md`: traspaso completo.
- `docs/CLAUDE_START_PROMPT.md`: mensaje inicial recomendado para Claude.
- `docs/A1_LEGISLATION_AUDIT.md`: auditoria normativa A1.
- `docs/CURRENT_STATUS.md`: estado operativo.
- `docs/DRIVE_IMPORT_CANDIDATES.md`: inventario de Drive.
- `docs/ROADMAP.md`: fases previstas.
