# Runbook de tareas largas, Streamlit y browserbatch

Este runbook evita confundir una tarea larga de QA visual/browserbatch con un bloqueo real.
El objetivo es observar antes de reiniciar, dejar logs utiles y no tocar BD ni mapping juridico.

## Principios

- No asumir bloqueo solo por tardanza.
- No reiniciar Streamlit en bucle.
- No matar procesos sin confirmar que no hay trabajo vivo.
- No ejecutar `apply_mapping_review.py --apply` durante QA visual.
- No modificar `db/gvadicto.sqlite`, `articles`, parser ni normalizacion.
- Registrar progreso y errores exactos.

## Herramientas

### Monitor de tareas largas

Envuelve comandos largos y escribe logs completos en `logs/`.

```powershell
python scripts/long_task_monitor.py -- python scripts/report_mapping_status.py
```

Para browserbatch/QA CLI:

```powershell
python scripts/long_task_monitor.py -- <comando-browserbatch>
```

El log incluye:

- hora de inicio,
- comando,
- duracion,
- stdout/stderr,
- ultimo output,
- periodos sin output,
- exit code.

### Diagnostico Streamlit

```powershell
python scripts/streamlit_diagnose.py
```

Comprueba:

- si el puerto 8501 esta ocupado,
- PID/proceso,
- si parece Streamlit,
- URL probable,
- respuesta HTTP,
- ultimos logs encontrados,
- recomendacion.

No mata procesos.

### Healthcheck de app

```powershell
python scripts/app_healthcheck.py
```

Con HTTP:

```powershell
python scripts/app_healthcheck.py --url http://localhost:8501
```

Comprueba:

- BD accesible en modo read-only,
- tablas esenciales,
- conteos de temas/normas/articulos/mappings,
- `validate_article_quality.py`,
- `report_mapping_status.py`,
- hash BD antes/despues.

### Reporte QA visual

Plantilla vacia:

```powershell
python scripts/qa_session_report.py
```

Ejemplo con datos:

```powershell
python scripts/qa_session_report.py --topic "especial 18" --law "Ley 39/2015" --articles "69;97;98" --fallback no --fine-mapping yes --visual-result pass --capture "logs/screenshot.png" --notes "Se visualiza articulado delimitado."
```

Genera:

- `reports/qa_session_report.md`
- `reports/qa_session_report.json`

## Como distinguir tarea larga de bloqueo real

Probablemente es una tarea larga si:

- el proceso sigue vivo,
- hay salida reciente o heartbeats del monitor,
- Streamlit responde HTTP,
- browserbatch esta abriendo paginas/capturando pantallas,
- no hay exit code todavia.

Probablemente es bloqueo real si:

- no hay salida durante mucho tiempo y el monitor marca `state=silent`,
- el proceso no consume ningun recurso y no genera artefactos,
- Streamlit no responde y el diagnostico muestra proceso colgado,
- browserbatch devuelve error o timeout explicito,
- el mismo paso falla de forma reproducible.

## Cuando esperar

Esperar si:

- `long_task_monitor.py` muestra `state=alive`,
- Streamlit responde HTTP,
- se estan generando logs/capturas,
- el comando no ha dado exit code,
- el navegador automatizado esta cargando pantallas pesadas.

Recomendacion practica: hacer checkpoint textual cada 5-10 minutos con ultimo output, PID, URL y log.

## Cuando hacer checkpoint

Hacer checkpoint si:

- han pasado mas de 5 minutos,
- el usuario podria pensar que esta colgado,
- hay un paso browserbatch largo,
- se cambia de tema/norma revisada,
- aparece una advertencia no fatal.

Un checkpoint debe incluir:

- comando activo,
- PID si se conoce,
- ultimo output,
- artefactos generados,
- siguiente paso previsto.

## Cuando reiniciar Streamlit

Reiniciar manualmente solo si:

- `streamlit_diagnose.py` dice que el puerto no responde,
- no hay browserbatch vivo dependiente de esa sesion,
- el proceso no esta generando logs/capturas,
- el error es reproducible tras healthcheck,
- el usuario autoriza o la tarea lo exige claramente.

## Cuando no reiniciar

No reiniciar si:

- Streamlit responde HTTP,
- browserbatch sigue vivo,
- hay output reciente,
- el proceso esta ejecutando QA visual,
- el unico sintoma es que tarda.

## Comandos recomendados para Claude

Antes de QA visual:

```powershell
python scripts/streamlit_diagnose.py
python scripts/app_healthcheck.py --url http://localhost:8501
```

Durante tarea larga:

```powershell
python scripts/long_task_monitor.py -- <comando-largo>
```

Despues de QA:

```powershell
python scripts/qa_session_report.py --topic "<tema>" --law "<norma>" --articles "<articulos>" --fallback <yes|no|unknown> --fine-mapping <yes|no|unknown> --visual-result <pass|fail|pending> --notes "<resumen>"
```

Si falla:

```powershell
python scripts/streamlit_diagnose.py
python scripts/app_healthcheck.py --url http://localhost:8501
```

Reportar el error exacto, ruta del log y decision recomendada. No reiniciar en bucle.
