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

- 77 textos normativos oficiales.
- 11989 articulos/bloques.
- 156 fuentes catalogadas.
- 75 temas oficiales A1-01 2025 importados.
- 198 enlaces tema-fuente.
- 32 hallazgos abiertos de validacion fina.
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

Comandos de verificacion:

python -m compileall app.py src scripts

Vigilancia normativa secuencial:

python scripts/check_source_updates.py --source-kind boe_consolidado --update-files
python scripts/check_source_updates.py --source-kind boe_pdf --update-files
python scripts/check_source_updates.py --source-kind dogv_pdf --update-files
python scripts/check_eurlex_versions.py --update-files --import-updated

Objetivo siguiente:

Quiero que sigamos con la validacion juridica fina tema por tema y que construyamos la futura interfaz de estudio descrita en `docs/STUDY_INTERFACE_SPEC.md`: temas ordenados por parte general/especifica, vista de tema con normativa concreta, anotaciones persistentes, comparacion tras cambios normativos y Pomodoro personalizable. Primero resuelve los hallazgos abiertos, especialmente EUR-Lex para Carta UE/RGPD/Reglamento UE-Euratom 2024/2509, y despues prepara un mapeo tema -> normas -> articulos/bloques prioritarios. No amplias preguntas salvo sobre temas validados y siempre con fuente.

Nivel de rigor: extremadamente alto para validacion juridica; alto para generar preguntas una vez validado.

Empieza orientandote, ejecuta solo lecturas/verificaciones al principio, dime el estado que encuentras y propon el primer cambio concreto con archivos y verificacion.
```
