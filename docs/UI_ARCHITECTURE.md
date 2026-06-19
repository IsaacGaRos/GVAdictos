# UI Architecture

## Situacion actual

- `app.py` sigue siendo una aplicacion Streamlit monolitica.
- La UI principal esta organizada en 9 pestanas: inicio, fuentes, importacion, articulos, preguntas, estudio, test, fallos e informes.
- La logica juridica y el flujo de estudio ya conviven en la misma pantalla, aunque la nueva infraestructura UI queda preparada fuera de `app.py`.
- No se ha integrado aun `src/ui` en la UI principal.

## Infraestructura propuesta

No se deja codigo UI nuevo en esta consolidacion. Propuesta futura:

- `src/ui/branding.py`: constantes visibles de marca.
- `src/ui/theme.py`: tokens de tema claro/oscuro, colores, espaciado, radios y sombras.
- `src/ui/typography.py`: tokens de familia, tamanos, pesos, line-height y spacing.
- `src/ui/assets.py`: registry de rutas esperadas para logo, favicon, iconos, splash e imagenes.
- `src/ui/study_adapters.py`: puente futuro hacia `StudyService` sin tocar logica juridica.

## Quick Wins

1. Cambiar `app.py` para importar `APP_NAME` desde `src/ui/branding.py`.
2. Inyectar CSS generado por `css_variables(get_theme(...))` y `typography_css(...)`.
3. Sustituir textos repetidos de marca por constantes.
4. Separar la pestana Estudiar en componentes por articulo, anotaciones y estado.
5. Capturar `StudySchemaMissingError` y mostrar aviso no intrusivo si la migracion de estudio no esta aplicada.

## Riesgos

- Refactorizar `app.py` entero ahora aumentaria el riesgo de pisar cambios de Claude.
- Aplicar estilos CSS globales a Streamlit puede afectar tablas y widgets nativos si no se prueba visualmente.
- Integrar `StudyService` antes de migrar la BD real produciria errores controlados, pero no experiencia completa.
- No tocar `topic_sources` desde UI: el estudio debe consumir mappings, no recalcularlos.

## Orden recomendado

1. Validar que Claude termino su fase juridica activa.
2. Aplicar migracion real de estudio solo con permiso del usuario.
3. Integrar branding constants en `app.py`.
4. Inyectar tokens CSS con un toggle claro/oscuro simple.
5. Integrar `StudyService` solo en la pestana Estudiar.
6. Hacer QA visual desktop y movil.
7. Crear acceso directo Windows cuando el usuario entregue icono final.
