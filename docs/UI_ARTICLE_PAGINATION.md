# Paginacion de articulos en Estudio

## Problema corregido

La UI de estudio truncaba la vista "Ver toda la norma sin delimitar" a los primeros 60 articulos. En normas largas, por ejemplo con 168 articulos, no habia navegacion para consultar los restantes.

## Solucion aplicada

Se sustituyo el corte fijo por paginacion en `app.py`:

- tamano por defecto: 30 articulos por pagina;
- opciones: 20, 30, 50 o 100;
- selector de pagina;
- contador visible `Mostrando articulos X-Y de N`;
- orden mantenido desde la consulta existente: `CAST(article_ref AS INTEGER), article_ref`.

## Alcance

La correccion afecta solo a la presentacion de la norma completa cuando un tema no tiene delimitacion fina de articulos.

No modifica:

- `articles`;
- `topic_sources`;
- parser/importer;
- normalizacion;
- mapping juridico;
- base de datos.

## Criterio de aceptacion

Una norma con 168 articulos debe permitir navegar por todos ellos desde el expander de norma completa. Con el valor por defecto se vera en 6 paginas: 30 + 30 + 30 + 30 + 30 + 18.
