# Launcher Windows - GVAdictos

## Objetivo

Permitir abrir GVAdictos desde el escritorio de Windows con doble click, sin infraestructura externa y sin tocar la base de datos ni la capa juridica.

## Archivos

- `scripts/launch_gvadictos.ps1`: abre la app Streamlit local.
- `scripts/launch_gvadictos.cmd`: wrapper compatible con doble click y accesos directos.
- `scripts/install_windows_launcher.ps1`: crea o regenera `GVAdictos.lnk` en el escritorio.

## Instalacion o regeneracion

Desde la raiz del proyecto:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/install_windows_launcher.ps1
```

El acceso directo queda en:

```text
%USERPROFILE%\Desktop\GVAdictos.lnk
```

## Icono

El instalador usa el primer icono `.ico` disponible en este orden:

1. `assets/icons/gvadictos.ico`
2. `assets/logo/gvadictos.ico`
3. `assets/icons/favicon.ico`
4. `Downloads/assets/**` si encuentra un `.ico` con nombre compatible.

Si no existe icono oficial, el acceso directo se crea igualmente con icono por defecto. Para activar icono despues, colocar el archivo oficial en `assets/icons/gvadictos.ico` y volver a ejecutar el instalador.

## Comportamiento

El launcher:

- entra en la raiz del proyecto;
- usa `.venv\Scripts\python.exe` si existe;
- si no hay `.venv`, usa `python` del sistema;
- abre `app.py` con Streamlit en `http://localhost:8501`;
- si la app ya responde en esa URL, abre el navegador y no arranca otra instancia.

## Limites

- No instala dependencias.
- No crea servicios de Windows.
- No modifica `db/gvadicto.sqlite`.
- No toca parser, importer, mappings, `articles` ni `topic_sources`.
