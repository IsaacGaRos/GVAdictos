# Handoff corto para Claude - tareas largas y QA visual

No asumas bloqueo por tardanza. Si una tarea browserbatch/QA visual tarda, primero observa.

## Antes de reiniciar nada

Ejecuta:

```powershell
python scripts/streamlit_diagnose.py
python scripts/app_healthcheck.py --url http://localhost:8501
```

Si Streamlit responde HTTP y el proceso parece vivo, continua.

## Para comandos largos

Lanza el comando envuelto:

```powershell
python scripts/long_task_monitor.py -- <comando-largo>
```

El monitor escribe logs en `logs/` con stdout, stderr, ultimo output, duracion y exit code.

## Durante browserbatch

- No reinicies Streamlit en bucle.
- No mates procesos si hay salida reciente o capturas nuevas.
- Haz checkpoint si tarda mas de 5-10 minutos.
- Reporta PID, ultimo output y ruta del log.
- Continua si el monitor marca `alive`.

## Si falla

Reporta:

- comando exacto,
- exit code,
- ultimo output,
- ruta del log,
- si Streamlit respondia HTTP,
- decision recomendada.

## Al terminar QA visual

Registra la sesion:

```powershell
python scripts/qa_session_report.py --topic "<tema>" --law "<norma>" --articles "<articulos>" --fallback <yes|no|unknown> --fine-mapping <yes|no|unknown> --visual-result <pass|fail|pending> --notes "<resumen>"
```

No hagas mapping juridico, no modifiques `db/gvadicto.sqlite`, no toques `articles`, no reimportes normas y no ejecutes `apply_mapping_review.py --apply`.
