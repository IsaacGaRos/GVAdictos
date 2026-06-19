# GVAdictos

App local-first para estudiar la oposicion A1-01 GVA 2025. Este MVP prioriza normativa trazada, estudio por temas, preguntas tipo test con fuente, registro de fallos y exportacion local.

## Instalacion

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Ejecutar

```powershell
streamlit run app.py
```

La base SQLite se crea en `db/gvadicto.sqlite`.

## Traspaso a Claude Code

Para continuar el proyecto en Claude Code:

- Lee `CLAUDE.md`.
- Lee `docs/CLAUDE_HANDOFF.md`.
- Lee `docs/STUDY_INTERFACE_SPEC.md`.
- Usa `docs/CLAUDE_START_PROMPT.md` como mensaje inicial.

## Que funciona en esta fase

- Importar leyes desde `.txt` o `.md`.
- Guardar copia intacta en `data/sources/leyes_originales`.
- Extraer articulos cuando el texto contiene encabezados tipo `Articulo 1`, `Artículo 1` o `Art. 1`.
- Ver y buscar articulos importados.
- Crear, editar y eliminar preguntas manuales.
- Crear preguntas desde un articulo fuente.
- Resolver preguntas en modo test.
- Registrar intentos, aciertos, fallos, causa de error y comentario.
- Ver resumen de fallos por pregunta.
- Ver informe basico semanal.
- Exportar preguntas, intentos y CSV basico para Anki.
- Catalogar fuentes oficiales y vigilar cambios semanales en BOE/DOGV/EUR-Lex.

## Que no funciona aun

- Google Calendar, Google Tasks o ICS.
- Planificacion adaptativa.
- Simulacros configurables.
- Generacion automatica avanzada de preguntas.
- Comparacion juridica entre convocatoria 2025 y 2026.

## Reglas de contenido juridico

- No inventar contenido juridico.
- Toda pregunta debe tener fuente.
- Las preguntas creadas con ayuda de IA deben marcarse como `requiere_revision`.
- Si un articulo no se puede clasificar con seguridad, queda como `pendiente_de_validacion`.

## Scripts utiles

```powershell
python scripts/import_law.py .\data\sources\leyes_originales\ley.txt --name "Ley ejemplo"
python scripts/import_source_manifest.py .\data\sources\drive_inventory\opo_temario_aula_virtual_2026.csv
python scripts/import_boe_pdf_laws.py
python scripts/build_extra_sources_manifest.py
python scripts/import_official_sources.py
python scripts/check_source_updates.py --source-kind boe_consolidado --update-files
python scripts/check_source_updates.py --source-kind dogv_pdf --update-files
python scripts/check_eurlex_versions.py --update-files --import-updated
python scripts/export_anki.py
python scripts/backup.py
```
