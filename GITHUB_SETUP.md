# GitHub Integration Setup - GVAdictos

Último paso para conectar tu repositorio local a GitHub.

## Estado actual
- ✅ Git inicializado
- ✅ GitHub CLI instalado
- ✅ Primer commit creado (sin empujar aún)
- ⏳ **NECESARIO:** Autenticación en GitHub CLI

## Pasos para completar

### 1. Abre PowerShell y ejecuta:

```powershell
& "C:\Program Files\GitHub CLI\gh.exe" auth login
```

### 2. Sigue las indicaciones:

```
? What account do you want to log into? GitHub.com
? What is your preferred protocol for Git operations? HTTPS
? Authenticate Git with your GitHub credentials? Yes
? How would you like to authenticate GitHub CLI? Login with a web browser
```

Se abrirá un navegador. Haz clic en "Authorize github" y espera a que confirme.

### 3. Una vez autenticado, verifica:

```powershell
& "C:\Program Files\GitHub CLI\gh.exe" auth status
```

Deberías ver:
```
github.com
  ✓ Logged in to github.com with HTTPS protocol (git https)
  ✓ Git operations for github.com configured to use https protocol.
```

### 4. Haz push del primer commit:

```powershell
cd C:\Users\isaac\Desktop\GVAdictos
git push -u origin master
```

### 5. Verifica en GitHub:

Abre https://github.com/IsaacGaRos/GVAdictos - deberías ver tu código

---

## Después: Workflow Code + PRO

Ambos chats sincronizan así:

**Antes de trabajar:**
```powershell
cd C:\Users\isaac\Desktop\GVAdictos
git fetch origin
git pull origin master
```

**Para empujar cambios:**
```powershell
git add .
git commit -m "tu mensaje"
git push origin master
```

**Para crear PR desde Claude:**
```powershell
git checkout -b feature/nombre-feature
git push origin feature/nombre-feature
# Claude puede usar: gh pr create --title "..." --body "..."
```

---

## Ayuda rápida

```powershell
# Ver status
git status

# Ver commits
git log --oneline

# Ver remote
git remote -v

# Ver branches
git branch -a

# Autenticación GitHub CLI
& "C:\Program Files\GitHub CLI\gh.exe" auth status

# Crear feature branch
git checkout -b feature/xyz

# Cambiar a master y actualizar
git checkout master
git pull origin master
```

---

**¡Una vez completado, los dos chats podrán trabajar en sincronia sin copiar/pegar!**
