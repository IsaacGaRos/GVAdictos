# Candidatos de Google Drive para importar

Fecha de revision: 2026-05-29

Origen revisado: Google Drive, `Mi Unidad -> Opo`.

## Carpetas principales encontradas

- `Opo/Autentica`
- `Opo/EraCEF`

## Prioridad alta

Estos elementos parecen mas utiles para actualizar fuentes del MVP antes de importar preguntas:

- `Opo/EraCEF/TemarioAulaVirtualCompleto`
  - Carpeta creada en 2026-03.
  - Subcarpetas:
    - `General`
    - `Especial`
  - Candidata principal para revisar temario actualizado.

- `Opo/EraCEF/TemarioAulaVirtualCompleto/General`
  - Subcarpetas:
    - `1- Constitucional`
    - `2- Organizacion Comunidad Valenciana`
    - `3- UE`
    - `4- Materias Transversales`

- `Opo/EraCEF/TemarioAulaVirtualCompleto/Especial`
  - Subcarpetas:
    - `1- Administrativo`
    - `2- Gestion Publica`
    - `3- Regimen de Empleados Publicos`
    - `4- Gestion Economico-Presupuestaria`
    - `5- UE`
    - `6- Competencias`

- `Opo/Autentica/Legislacion A1 2025 v4.pdf`
  - PDF de legislacion consolidada o recopilada.
  - Creado en Drive en 2026-02, modificado en 2025-10.
  - Requiere conversion PDF -> texto antes de importar al MVP.

- `Opo/Autentica/Administrativo/ARTICULOS ESENCIALES: BLOQUE ADMINISTRATIVO (A1 GVA)`
  - Google Doc creado/modificado en 2026-02.
  - Candidato para extraer listado de articulos clave.

## Prioridad media

- `Opo/Autentica/Funcion Publica`
  - Contiene normativa y guias de funcion publica:
    - `Guia Funcion Publica`
    - `Dudas`
    - `1- TREBEP`
    - `2- LFPV`
    - `Ley 31-1995 LPrevencionRiesgosLaborales.pdf`
    - `RD 33-1986 Regimen Disciplinario.pdf`
    - `Decreto 49-2021 Teletrabajo.pdf`
    - `Decreto 42-2019 Permisos.pdf`
    - `Decreto 3-2017 Carrera.pdf`
    - `Ley 53-84 Incompatibilidades.pdf`
  - Material util, pero parte puede solaparse con el archivo local.

- `Opo/EraCEF/Temario`
  - Subcarpetas de temario clasico:
    - `Administrativo`
    - `Autonomico-Transversales`
    - `Gestion Economico Presupuestaria`
    - `Gestion Publica`
    - `Local`
    - `Recursos Humanos`
    - `Union Europea`
    - `Test-A1-GVA`
  - Probablemente comparable al archivo local, pero menos reciente que `TemarioAulaVirtualCompleto`.

## Cambios normativos detectados como candidatos

En `Opo/Autentica` aparecen varios PDFs de cambios normativos creados/modificados a finales de 2025:

- `Mods LJCA dic 2023.pdf`
- `Cambios LHPV Medidas 2024.pdf`
- `Cambios LFPV Medidas 2024 (1).pdf`
- `Mod Ley Incompatibilidades.pdf`
- `decreto7_2024.pdf`
- `Transparencia_Cambios.pdf`
- `ley 6-2024-simplificacion advta.pdf`
- `modif varias DL142025.pdf`

Estos documentos no deben importarse como texto definitivo sin revisar fuente oficial y estado de vigencia.

## No prioritario para MVP

- Facturas, justificantes y pagos.
- Simulacros A1/practicos salvo que se quiera alimentar el modulo de tests mas adelante.
- Presentaciones antiguas o materiales universitarios no vinculados directamente a C2/A1 GVA.

## Recomendacion de siguiente importacion

1. Revisar `Opo/EraCEF/TemarioAulaVirtualCompleto/General` y `Especial`.
2. Identificar dentro de esas carpetas los PDFs o Docs correspondientes a normas concretas.
3. Convertir solo 1-2 documentos piloto a TXT/MD.
4. Importarlos en GVAdictos y validar si el parser de articulos funciona con ese formato.
5. Mejorar el importador PDF/Docs solo despues de ver el formato real.

## Catalogo cargado en GVAdictos

Se creo un manifiesto local en `data/sources/drive_inventory/opo_temario_aula_virtual_2026.csv` con 60 PDFs de `Opo/EraCEF/TemarioAulaVirtualCompleto`.

El manifiesto se cargo en SQLite con:

```powershell
python scripts/import_source_manifest.py data\sources\drive_inventory\opo_temario_aula_virtual_2026.csv
```

Todas las fuentes quedan con `legal_status = pendiente_de_validacion`. Esto evita afirmar que una norma esta vigente o entra en convocatoria sin revisar bases y fuente oficial.
