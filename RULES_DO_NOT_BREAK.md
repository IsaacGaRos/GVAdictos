# RULES_DO_NOT_BREAK — GVAdictos

Reglas innegociables. Romper una de estas es un fallo grave. (Derivadas de `CLAUDE.md` + aprendizajes de sesión.)

## Idioma y trato
1. **Responder SIEMPRE en español (es-ES).** Sin excepciones.

## Rigor jurídico (máxima prioridad)
2. **No inventar contenido jurídico.** Toda pregunta/explicación/mapeo artículo debe tener fuente.
3. **El ranking de "más preguntado" usa SOLO exámenes oficiales GVA.** Nunca simulacros de academia (TSGV, EraCEF, Auténtica). Marcador: `exam_papers.fuente_tipo='oficial_gva'`.
4. **Todo mapeo IA/OCR/inferido se marca `requiere_revision_humana`** (o `pendiente_revision_humana`) y con confianza acorde. Nunca presentarlo como validado.
5. **No modificar originales** en `data/sources/leyes_originales`.
6. Textos consolidados BOE/EUR-Lex son informativos; la versión auténtica es la oficial publicada (BOE/DOGV/DOUE).

## Invariantes técnicos
7. **Invariante del ranking: toda pregunta oficial tiene ≥1 artículo vinculado.** Verificar con `infer_global_fallback.py` (imprime "sin artículo=0"). No commitear si se rompe.
8. **No cachear conexiones SQLite** entre reruns de Streamlit; usar `connect()` (devuelve `DictRow`). Hacer `commit` en mutaciones.
9. El pipeline del ranking debe ejecutarse en orden (ver `run_exam_pipeline.py`); `rebuild_official_exams.py` BORRA y reconstruye las tablas derivadas — `ocr_exam_loader` va DESPUÉS (apéndice).
10. Tras tocar `app.py`/`src`/`scripts`: `python -m compileall app.py src scripts` debe dar exit 0.

## Repo / proceso
11. Cambios pequeños, verificables y documentados. Commit solo cuando el usuario lo pida o al cerrar un hito (esta sesión lo pidió).
12. **No meter credenciales** en el repo. Usar `.env`.
13. **No subir PDFs gigantes innecesarios** (p.ej. el combinado 63-64_18 de 13 MB): extraer plantilla a `.txt`, cachear OCR en `.txt`, borrar el PDF fuente.
14. Co-Authored-By en commits: `Claude Opus 4.8 <noreply@anthropic.com>`.

## Producto
15. **A partir de 2026-06-22 la prioridad es el USO DIARIO de estudio.** No iniciar funcionalidades grandes nuevas sin que lo necesario para el ritmo diario esté cerrado. Alinear con la planificación mensual de Academia Auténtica (la enviará el usuario).
16. Autténtica = señal académica auxiliar de alta prioridad (obtuvo ~75% de plazas), pero NUNCA autoridad jurídica final.
