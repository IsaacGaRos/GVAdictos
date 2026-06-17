# AGENTS.md - GVAdicto

## Objetivo

GVAdicto es una app local para preparar oposiciones GVA, especialmente C2 GVA.

## Reglas criticas

- No inventar contenido juridico.
- Toda pregunta o explicacion debe tener fuente.
- No modificar leyes originales.
- El directorio local `Archivo Oposicion TAG-GVA` puede estar desactualizado.
- Para materiales mas actualizados, revisar Google Drive en `Mi Unidad -> Opo` cuando el usuario pida importar, comparar o actualizar fuentes.
- Trabajar con cambios pequenos y verificables.
- Priorizar MVP funcional.
- No implementar LifeHub/gym/dieta por ahora.
- No usar APIs externas sin modo mock/fallback.
- Guardar credenciales solo en `.env`.
- No versionar tokens.

## Gestion de consumo

- Trabajar por defecto en inteligencia Media.
- Velocidad Estandar.
- Clasificar cada tarea antes de ejecutarla.
- Si una subtarea requiere Alta o Extremadamente alta, pausar y pedir nueva tarea con ese nivel.
- No leer todo el repo salvo instruccion expresa.
- No hacer refactors globales sin permiso.

## Flujo

Antes de tocar codigo:

1. Resumir tarea.
2. Indicar nivel recomendado.
3. Indicar archivos minimos.
4. Indicar verificacion.
5. Ejecutar solo si el nivel actual basta.

Al final:

- Cambios.
- Archivos tocados.
- Verificacion.
- Riesgos.
- Siguiente paso.
