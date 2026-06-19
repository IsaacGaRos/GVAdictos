# GVAdictos — Punto de arranque para la próxima sesión

> Pega el bloque "PROMPT DE ARRANQUE" como primer mensaje tras hacer `/clear`.
> Última actualización: 2026-06-19.

## Read First
1. `CLAUDE.md`
2. Tu memoria: `MEMORY.md` (índice) + `project_fase2f_completada.md`
3. `docs/VISION_ARQUITECTURA_PRODUCTO_2026.md` (arquitectura de futuro)

No releas todo el repo. No rehagas la validación de artículos salvo duda concreta.

---

## Estado al cerrar esta sesión

**Núcleo del proyecto (delimitación fina tema→norma→artículo): CERRADO AL 100%.**

- **75/75 temas** con delimitación fina (`topic_sources.article_id`).
- `topic_sources`: 3.961 filas. `validate_article_quality.py` = **PASS**. check #6 (conjuntos idénticos) = **0**. FK rotas = **0**. **Fallback: 0/75.**
- Artículos en BD: 6.794. Leyes: 82 (incluye nueva: Código Civil id=97).

### Fases completadas hoy (sesión Sonnet 2026-06-19)

| Fase | Qué se hizo |
|---|---|
| **2N** gen-13 TUE fix | UPDATE arts TUE 1-5 (contaminados con texto de Protocolos) con texto real del HTML EUR-Lex. Mapeo gen-13 → TUE arts 1-6. |
| **2O** esp-26 Carta DDFF | INSERT Carta DDFF art. 41 (derecho a buena administración) desde HTML EUR-Lex. Mapeo esp-26. |
| **2P** esp-28 planificación | Mapeo a arts existentes: Ley 50/1997 art. 25 + Ley 19/2013 art. 6 + Ley 6/2024 art. 38. |
| **2Q** esp-5 CC art. 2 | Descarga CC PDF BOE, extrae art. 2, crea ley CC en BD (id=97), mapeo esp-5 → CC art. 2 + CE art. 9. LPAC eliminado de esp-5. |

Scripts: `scripts/apply_fase2n_gen13_tue_fix.py`, `apply_fase2o_esp26_carta_ddff_art41.py`, `apply_fase2p_esp28_planificacion.py`, `apply_fase2q_esp5_cc_art2.py`

### No quedan temas irreductibles. La tabla de "4 irreductibles" está liquidada.

---

## Reglas críticas vigentes (CLAUDE.md)

- No tocar parser/importer/`articles`/`topic_sources` salvo cambios aditivos con backup + dry-run + `validate_article_quality.py` en PASS.
- No borrar mappings ajenos (solo los del propio `mapping_basis`). Respetar IDs protegidos.
- Fuente oficial ≠ material académico (CEF/Autentica); todo derivado/IA nace `requiere_revision`/`pendiente_de_validacion`.
- No inventar contenido jurídico; toda afirmación con fuente.

---

## PROMPT DE ARRANQUE (copiar tras `/clear`)

```
Proyecto GVAdictos (oposiciones A1-01 GVA 2025), app Streamlit local + SQLite en db/gvadicto.sqlite.
Lee primero tu memoria (MEMORY.md) y .claude/NEXT_CHAT_START_HERE.md para el contexto.

ESTADO: la delimitación fina tema→norma→artículo está CERRADA AL 100%: 75/75 temas,
topic_sources 3.961 filas, validate_article_quality PASS, fallback=0, FK=0, check#6=0.
Hoy se cerró la sesión Sonnet cerrando los 4 últimos temas irreductibles (gen-13 TUE fix,
esp-26 Carta DDFF art.41, esp-28 planificación A, esp-5 CC art.2). No quedan irreductibles.

REGLAS: no tocar parser/importer/articles/topic_sources salvo cambios aditivos con backup +
dry-run + validate_article_quality en PASS; no borrar mappings ajenos; fuente oficial ≠ academia;
todo derivado/IA = requiere_revision. No inventar contenido jurídico.

QUÉ QUIERO HACER AHORA (elige una vía y dímela):
  A) Empezar a implementar la arquitectura de producto de docs/VISION_ARQUITECTURA_PRODUCTO_2026.md,
     por la Ola A (cimientos de estudio): A1 migrar src/study a BD real, A2 estructura jerárquica
     law_divisions, A3 referencias "en grupo" topic_source_segments.
  B) Banco de exámenes oficiales (Ola B): esquema + 1-2 convocatorias piloto + vinculación
     Pregunta→Artículo→Ley→Tema.
  C) Otra cosa.

Antes de implementar nada que toque BD, propón el diseño y espera mi OK; trabaja en cambios
pequeños, verificables y con backup.
```

---

## Notas para el asistente de la próxima sesión

- **Vía A (arquitectura):** la migración de `src/study` (`study_article_notes`, `study_highlights`, `study_progress`, `study_marks`, `study_last_reviews`) ya está diseñada en `src/study/schema.py` con el patrón `anchor_key`/snapshot — primer paso natural y de bajo riesgo (aditivo).
- **Código Civil:** importado como stub mínimo (solo art. 2). Si en el futuro se quiere importar el CC completo, hay que hacerlo con backup obligatorio y sin borrar el art. 2 existente (id=104991, law_id=97).
- **TUE arts 7-8:** siguen contaminados con texto de Protocolos (Protocolo subsidiariedad y Protocolo Dinamarca). No eran necesarios para ningún tema del temario A1, pero si algún día se importan hay que tratarlos igual que 2N.
- **Material académico (CEF):** PE-51..60 tienen temario CEF 2026 en `topic_study_resources`. Drive unidad **F:** activo.
- **Documentación de futuro:** `docs/VISION_ARQUITECTURA_PRODUCTO_2026.md` — solo diseño, no implementado.
