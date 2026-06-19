# Prompt generico de resincronizacion para Claude Code

Usa este prompt cuando Codex haya avanzado el proyecto y quieras que Claude Code se actualice sin cargar una conversacion larga.

```text
Estoy trabajando en el repositorio local `GVAdictos`.

Necesito que te resincronices con el estado actual SIN leer todo el repo y SIN arrastrar contexto antiguo.

Reglas:
- No inventes contenido juridico.
- No modifiques parser/importer/normalizacion sin permiso explicito.
- No reimportes normas sin permiso explicito.
- No toques `articles` ni `topic_sources` salvo que la tarea lo autorice expresamente.
- Si hay mapping o BD, primero dry-run/preflight y backup.
- Si detectas contradiccion con este prompt, para y pregunta.

Lee solo estos documentos, en este orden:
1. `docs/CLAUDE_KNOWLEDGE_DUMP.md`
2. `docs/SYSTEM_STABILITY_FREEZE.md`
3. `reports/mapping_status.md`
4. `.claude/PILOTO_FASE2E_PE13_DELIMITACION.md`
5. el documento especifico de la tarea que te pida despues

Estado reciente que debes asumir hasta comprobarlo:
- Fase 2D corrigio Ley 40/2015 arts. 24-27 in-place, con `article_id` estables.
- Fase 2E PE-13 ya fue aplicada por Codex.
- PE-13 = `topic_id=28`.
- Mapping PE-13 aplicado:
  - Ley 40/2015 law_id 4: arts. 1-53 y 140-158.
  - Decreto 176/2014 law_id 27: arts. 1-21.
  - `mapping_basis = validacion_articulos_claude_fase2e_pe13_2026_06_18`.
- Ultimo estado esperado:
  - 81 leyes.
  - 6792 articulos.
  - 75 temas.
  - 1286 `topic_sources`.
  - 1079 enlaces con `article_id`.
  - 16 temas con mapping fino.
  - `validate_article_quality.py` en PASS.
  - FKs rotas = 0.

Antes de cualquier tarea nueva ejecuta:
python scripts/validate_article_quality.py
python scripts/report_mapping_status.py

Despues dime:
- estado real observado;
- si coincide con el estado esperado;
- archivos minimos que necesitas leer para la tarea concreta;
- modelo/nivel recomendado;
- plan minimo en 3-5 pasos;
- riesgos.

No hagas cambios todavia hasta que te diga la tarea concreta.
```

## Prompt corto si Claude tiene poca ventana

```text
Repo: GVAdictos. No leas todo. Lee solo `docs/CLAUDE_SYNC_PROMPT.md`, `reports/mapping_status.md` y la tarea concreta.

Estado clave: PE-13 ya aplicado por Codex con `mapping_basis=validacion_articulos_claude_fase2e_pe13_2026_06_18`; topic_sources=1286; fine mappings=1079; temas con mapping fino=16; validate_article_quality PASS. No tocar parser/importer/articles/topic_sources salvo permiso explicito. Ejecuta primero `python scripts/validate_article_quality.py` y `python scripts/report_mapping_status.py`.
```
