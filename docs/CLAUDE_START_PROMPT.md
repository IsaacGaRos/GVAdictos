# Mensaje inicial para Claude Code

Copia y pega este mensaje al iniciar Claude Code en `C:\Users\isaac\Desktop\GVAdictos`.

```text
Estoy migrando este proyecto desde Codex a Claude Code. Trabaja desde el workspace:

C:\Users\isaac\Desktop\GVAdictos

Primero lee:

1. CLAUDE.md
2. docs/CLAUDE_HANDOFF.md
3. docs/A1_LEGISLATION_AUDIT.md
4. docs/CURRENT_STATUS.md
5. README.md

Contexto breve:

GVAdicto es una app local-first en Python + Streamlit + SQLite para preparar oposiciones GVA, con foco actual en A1-01 GVA 2025. Ya hay normativa oficial importada desde BOE/DOGV/EUR-Lex y una validacion fina tema-fuente iniciada:

- 80 textos normativos oficiales.
- 12838 articulos/bloques.
- 156 fuentes catalogadas.
- 75 temas oficiales A1-01 2025 importados.
- 204 enlaces tema-fuente.
- 23 hallazgos abiertos de validacion fina.
- Preguntas: 20 piloto desde Ley 39/2015, con fuente y todas `requiere_revision=1`.
- Intentos: 0.

Reglas criticas:

- No inventes contenido juridico.
- Toda pregunta/resumen/explicacion debe tener fuente.
- No uses documentos de academia o Drive como fuente juridica definitiva sin contrastar BOE/DOGV/EUR-Lex.
- No modifiques originales en data/sources/leyes_originales.
- Todo contenido juridico queda pendiente_de_validacion hasta revision humana.
- No ejecutes watchers en paralelo porque SQLite puede bloquearse.
- No ejecutes check_source_updates.py para eurlex_html; usa scripts/check_eurlex_versions.py.
- Autentica se ha usado solo como contraste auxiliar de cobertura; sus mapeos llevan `autentica_auxiliar_pendiente_validacion`.
- El usuario indica que Autentica obtuvo el 75% de las plazas de la convocatoria pasada: usarla como senal auxiliar fuerte de prioridad, no como fuente juridica final.

Comandos de verificacion:

python -m compileall app.py src scripts

Vigilancia normativa secuencial:

python scripts/check_source_updates.py --source-kind boe_consolidado --update-files
python scripts/check_source_updates.py --source-kind boe_pdf --update-files
python scripts/check_source_updates.py --source-kind dogv_pdf --update-files
python scripts/check_eurlex_versions.py --update-files --import-updated

Objetivo siguiente:

Quiero avanzar hacia una aplicacion funcional de estudio con minimo gasto de tokens. No quiero ahora una auditoria juridica global. La pestaña `Estudiar` ya existe como navegador inicial de temas; revisala sin hacer refactors globales y avanza con el siguiente corte minimo: anotacion persistente simple vinculada a `topic_id` y/o `article_id`. Incluye en el diseno la posibilidad de seleccionar un fragmento y preguntar una duda a la IA mediante click derecho o accion contextual equivalente; la respuesta debe guardar fuente/contexto y marcarse como `requiere_revision`.

Nivel de rigor: extremadamente alto para validacion juridica; alto para generar preguntas una vez validado.

Empieza orientandote, ejecuta solo lecturas/verificaciones al principio, dime el estado que encuentras y propon el primer cambio concreto con archivos y verificacion.
```
