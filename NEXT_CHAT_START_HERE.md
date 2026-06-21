# NEXT_CHAT_START_HERE — GVAdictos

> Punto de entrada para un chat nuevo. Lee en este orden y podrás continuar sin contexto previo.

## 1. Orden de lectura
1. `RULES_DO_NOT_BREAK.md` — reglas innegociables (idioma, rigor jurídico, invariantes).
2. `CURRENT_BASELINE.md` — estado verificado y cómo arrancar/validar.
3. `MEMORY_COMPACT_DUMP.md` — volcado denso (decisiones, gotchas, cifras, pendientes).
4. `docs/EXAM_RANKING_PIPELINE.md` — detalle del pipeline de exámenes oficiales.
5. `CLAUDE.md` — rol y reglas del proyecto.

## 2. Estado en una línea
Plataforma de estudio A1-01 GVA funcional. Ranking de "lo más preguntado" COMPLETO para A1-01 (13 papers, 1185 preguntas oficiales, 0 sin artículo). Listo para uso diario.

## 3. Contexto crítico de producto (¡importante!)
- **Desde 2026-06-22 el usuario estudia a diario con GVAdictos como plataforma principal.**
- El usuario **enviará la planificación mensual de Academia Auténtica**; a partir de ahí, **el desarrollo se alinea con esa planificación**.
- Solo trabajar en contenido/funcionalidades extra cuando lo necesario para seguir el ritmo de la academia esté cerrado y quede tiempo.
- No iniciar funcionalidades grandes sin necesidad inmediata de estudio.

## 4. Siguiente tarea recomendada
**Esperar la planificación mensual de Auténtica** y, con ella, ejecutar la **Prioridad 1** del roadmap (uso diario sin fricciones). Si el usuario aún no la ha enviado, empezar por el repaso de fricciones de uso diario (ver ROADMAP P1) sobre la pestaña **Estudiar** y **🔥 Mas preguntado**.

## 5. Riesgos / pendientes abiertos
- A1-01 **22/15** no está online (cerrado, no recuperable por ahora).
- Artículos **inferidos (≈)** y preguntas **OCR**: necesitan revisión humana antes de tratarse como verdad jurídica.
- 2ª parte teórico-práctica de **C1-01 64/25** y otros cuerpos (A2-01, C2-01) sin cargar (no prioritario; foco A1-01).
- OCR 2016 (31/16 71/120, 32/16 57/120): cobertura parcial por mala calidad de escaneo.

## 6. Comandos
```powershell
python -m streamlit run app.py          # arrancar (o launcher.bat -> 1)
python scripts/run_exam_pipeline.py     # reconstruir ranking (o launcher.bat -> 4)
python -m compileall app.py src scripts # validar compilación
```

## 7. Roadmap
Ver bloque `# ROADMAP PRIORIZADO` al final de este archivo.

---

# ROADMAP PRIORIZADO

Objetivo rector: **GVAdictos como plataforma diaria de estudio**, alineada con la planificación de Auténtica. Orden = mayor impacto en el estudio diario primero.

## Prioridad 1 — Uso diario sin fricciones (hacer primero)
- **Importar la planificación mensual de Auténtica** a un plan de estudio dentro de la app (tema/fecha) y que la pestaña Estudiar/Plan lo refleje como "qué toca hoy".
- **Flujo diario de una pantalla**: abrir app → ver el tema del día (según Auténtica) → estudiar artículos (incluido "más preguntado" del tema) → registrar repaso. Minimizar clics.
- **Verificar a fondo la pestaña Estudiar y 🔥 Mas preguntado** con uso real: que abrir tema → normativa/artículos → estudiar funcione fluido; corregir cualquier fricción.
- **Persistencia fiable de progreso** (lo estudiado/pendiente hoy) y que sobreviva reruns de Streamlit.

## Prioridad 2 — Memorización, comprensión y repaso
- **Repetición espaciada (SRS)** sobre artículos/preguntas (ya hay `srs_state`): cola diaria de repaso.
- **Banco de preguntas oficiales como modo test/repaso por tema** usando ya las 1185 preguntas cargadas (filtrando por tema/ley/artículo) — gran activo ya disponible.
- **Registro de fallos → repaso dirigido** (tabla `attempts`/Fallos ya existe): cerrar el bucle ver fallo → reestudiar artículo.
- Revisión humana asistida de artículos inferidos (≈) para subir calidad del ranking por tema.

## Prioridad 3 — UX, IA y automatización
- Acción contextual "preguntar duda a la IA" sobre un fragmento (guardar fuente, marcar `requiere_revision`).
- Mejoras de UX en Estudiar (filtros, contador por artículo, TTS del artículo del día).
- Vigilancia normativa automatizada (scripts ya existen) en cron/Task Scheduler.

## Prioridad 4 — Técnico / arquitectura (puede esperar)
- Mejorar reconstrucción OCR (más cobertura en 2016) y cargar otros cuerpos/convocatorias.
- Tests automatizados del pipeline de exámenes.
- Limpieza de documentación duplicada en `docs/` (muchos handoffs antiguos).
