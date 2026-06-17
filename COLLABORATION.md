# Collaboration Guide: Code + Claude PRO

Este repositorio es compartido entre dos sesiones de Claude:
- **Claude Code** (CLI, este chat)
- **Claude PRO** (web interface, otro chat)

Ambas trabajan aquí sin copiar/pegar. Objetivo: sincronización en tiempo real vía Git.

## Flujo básico

### Antes de empezar trabajo
```bash
git fetch origin
git pull origin master
```

### Si trabajas en cambios grandes
```bash
git checkout -b feature/nombre-descriptivo
# ... haz cambios ...
git add .
git commit -m "Descripción clara"
git push origin feature/nombre-descriptivo
```

### Si acabas, avisa al otro chat
```bash
# Opción 1: Merge a master (en GitHub UI o gh)
# Opción 2: Espera a que el otro chat pullée tu rama
```

## Ramas recomendadas

- `master` — estado estable, siempre funciona
- `feature/code-*` — cambios desde Code
- `feature/pro-*` — cambios desde Claude PRO
- `feature/validation-*` — validación de hallazgos
- `feature/questions-*` — generación de preguntas

## Reglas críticas (heredadas de CLAUDE.md)

⚠️ **NUNCA:**
- Inventar contenido jurídico
- Afirmar que una norma es vigente sin fuente oficial
- Modificar originales en `data/sources/leyes_originales/`
- Ejecutar watchers SQLite en paralelo (riesgo de bloqueo)

✅ **SIEMPRE:**
- Toda pregunta/afirmación jurídica necesita fuente
- Marcar preguntas con IA como `requiere_revision=1`
- Validar artículos exactos antes de preguntas
- Testear cambios localmente antes de push

## Estructura importante

```
GVAdictos/
├── app.py                          # Interfaz Streamlit
├── db/gvadicto.sqlite              # Base SQLite (TRACKEADA EN GIT)
├── data/sources/
│   ├── leyes_originales/           # Oficiales descargados (NO MODIFICAR)
│   └── processed/                  # Convertidos (OK modificar)
├── data/processed/official_sources/ # Textos convertidos
├── scripts/                        # Herramientas de importación
├── src/                            # Código núcleo
├── docs/
│   ├── CLAUDE_HANDOFF.md           # Traspaso completo
│   ├── A1_LEGISLATION_AUDIT.md     # Auditoría normativa
│   ├── CURRENT_STATUS.md           # Estado operativo
│   └── STUDY_INTERFACE_SPEC.md     # Especificación futura interfaz
├── CLAUDE.md                       # Instrucciones este proyecto
├── GITHUB_SETUP.md                 # Setup GitHub (Code)
└── COLLABORATION.md                # Este archivo
```

## Estado actual (2026-06-17)

| Métrica | Valor |
|---------|-------|
| Leyes importadas | 80 |
| Artículos/bloques | 12,838 |
| Temas A1-01 | 75 |
| Preguntas piloto | 20 (todas requiere_revision=1) |
| Hallazgos abiertos | 29 |
| Hallazgos resueltos (EUR-Lex) | 3 |

## Últimos cambios

```
65ae789 Initial commit: GVAdictos local setup with 80 laws, 12838 articles, EUR-Lex integration ready
```

Ver: `git log --oneline` para historial completo.

## Cómo sincronizar

**Code o PRO acaba de empujar cambios:**
```bash
# El otro chat ejecuta:
git fetch origin
git pull origin master
# O si está en rama feature:
git pull origin feature/nombre
```

**Hay conflictos (raro pero posible):**
```bash
# Manual:
git status  # Ver archivos en conflicto
# Edita manualmente
git add .
git commit -m "Resolve conflicts"
git push origin rama-actual

# O pídele al otro chat que resuelva via PR
```

## Para Claude PRO iniciando

1. **Lee primero:**
   - `CLAUDE.md`
   - `docs/CLAUDE_HANDOFF.md`
   - `docs/CURRENT_STATUS.md`

2. **Sincroniza:**
   ```bash
   git fetch origin && git pull origin master
   ```

3. **Crea rama si cambios grandes:**
   ```bash
   git checkout -b feature/pro-tu-trabajo
   ```

4. **Avisa al otro chat qué vas a hacer** (en tu sesión, vía comentario o documento)

5. **Pushea cuando acabes:**
   ```bash
   git push origin feature/pro-tu-trabajo
   ```

## Comandos útiles

```bash
# Ver estado
git status

# Ver remoto
git remote -v

# Ver ramas
git branch -a

# Ver commits recientes
git log --oneline -10

# Cambiar rama
git checkout rama-nombre

# Crear rama
git checkout -b feature/nuevo

# Descargar cambios remotos sin aplicar
git fetch origin

# Descargar y aplicar
git pull origin master

# Empujar tus cambios
git push origin rama-actual

# Ver diferencias
git diff master..feature/xyz

# Crear PR desde CLI
gh pr create --title "Título" --body "Descripción"

# Listar PRs
gh pr list

# Ver PR específico
gh pr view <número>
```

## Preguntas frecuentes

**¿Qué hago si Code empujó mientras yo estaba trabajando?**
```bash
git fetch origin
git rebase origin/master
# Resuelve conflictos si hay
git push origin -f feature/tu-rama
```

**¿Puedo trabajar ambos en master directamente?**
No recomendado. Usa feature branches. Evita conflictos.

**¿La BD SQLite se sincroniza?**
Sí, está trackeada. Pero ojo: cambios concurrentes en DB pueden causar conflictos. Comunicaos qué estáis modificando.

**¿Necesito instalar GitHub CLI en PRO?**
No. Code ya lo hizo. Tú solo usa git CLI estándar.

**¿Puedo borrar ramas después de mergear?**
Sí. GitHub sugiere "Delete branch" después de mergear PR. O: `git branch -d rama-local` y `git push origin --delete rama-remote`

---

**¡Bienvenidos! Empezamos sin copiar/pegar.** 🚀

Cualquier pregunta sobre el flujo, preguntad en el chat correspondiente.
