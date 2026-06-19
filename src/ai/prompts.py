"""Prompts versionados para generación de insights de IA.

Cada prompt es versionado para permitir reproducibilidad y cambios controlados.
Los cambios en prompts deben incrementar la versión.
"""

PROMPT_VERSION = "1.0"


def get_article_explanation_prompt(article_title: str, article_text: str) -> str:
    """Prompt para generar explicación sencilla de un artículo."""
    return f"""Eres un especialista en derecho administrativo que explica textos legales complejos de forma sencilla para opositores.

Artículo: {article_title}

Texto legal:
{article_text}

Tarea: Proporciona una explicación clara y breve (máximo 100 palabras) que un opositor pueda entender sin necesidad de formación jurídica previa.

Requisitos:
- Usa un lenguaje accesible
- Explica los conceptos principales
- Omite detalles secundarios
- No inventes información no presente en el artículo
- Termina indicando la fuente: "Fuente: Artículo {article_title}"

Explicación:
"""


def get_article_summary_prompt(article_title: str, article_text: str) -> str:
    """Prompt para generar resumen estructurado de un artículo."""
    return f"""Eres un especialista en derecho administrativo que crea resúmenes estructurados para estudio.

Artículo: {article_title}

Texto legal:
{article_text}

Tarea: Crea un resumen estructurado del artículo con esta estructura:

**Concepto clave:** [una frase con la idea principal]
**Elementos principales:**
- [elemento 1]
- [elemento 2]
- [elemento 3]

**Aplicación:** [breve párrafo sobre cuándo se aplica]
**Puntos clave para oposición:** [lista de 2-3 puntos que es probable que pregunten]

Requisitos:
- Máximo 150 palabras en total
- No inventes información
- Sé preciso con términos legales
- Termina indicando la fuente: "Fuente: Artículo {article_title}"

Resumen:
"""


def get_article_mnemonic_prompt(article_title: str, article_text: str) -> str:
    """Prompt para generar mnemotecnia de un artículo."""
    return f"""Eres un especialista en técnicas de memorización para opositores.

Artículo: {article_title}

Texto legal:
{article_text}

Tarea: Crea una o más técnicas mnemotécnicas (acrónimos, reglas, historias) que ayuden a recordar los puntos clave de este artículo.

Proporciona:
1. **Mnemotecnia principal:** [acrónimo o técnica]
2. **Explicación:** [cómo funciona]
3. **Ejemplo:** [un ejemplo de uso en contexto]

Requisitos:
- Las mnemotecnias deben ser fáciles de recordar
- Deben cubrir los elementos clave del artículo
- No inventes información
- Termina indicando la fuente: "Fuente: Artículo {article_title}"

Mnemotecnia:
"""


def get_article_comparison_prompt(
    article_title: str,
    article_text: str,
    related_articles: list[tuple[str, str]],
) -> str:
    """Prompt para comparar un artículo con otros relacionados."""
    related_text = "\n".join(
        f"**{title}:** {text[:200]}..." for title, text in related_articles[:3]
    )
    return f"""Eres un especialista en derecho administrativo que explica diferencias entre artículos.

Artículo principal: {article_title}

Texto:
{article_text}

Artículos relacionados:
{related_text}

Tarea: Compara el artículo principal con los relacionados. Responde:

**Similitudes:**
- [similitud 1]
- [similitud 2]

**Diferencias clave:**
- [diferencia 1]
- [diferencia 2]

**Cuándo confundirse:** [situación común donde se confunden]

Requisitos:
- Máximo 150 palabras
- Sé preciso con términos
- No inventes información
- Termina indicando: "Fuente: Artículos {article_title} y [relacionados]"

Comparación:
"""


def get_common_mistakes_prompt(article_title: str, article_text: str) -> str:
    """Prompt para identificar errores comunes sobre un artículo."""
    return f"""Eres un especialista en derecho administrativo y en análisis de errores de opositores.

Artículo: {article_title}

Texto legal:
{article_text}

Tarea: Identifica los 3-4 errores más comunes que cometen los opositores sobre este artículo.

Para cada error:
**Error común #1:** [descripción del error]
- **Por qué es erróneo:** [explicación]
- **Interpretación correcta:** [lo correcto]

Requisitos:
- Basa los errores en malinterpretaciones probables del texto
- Sé específico y útil para el estudio
- No inventes errores imposibles
- Máximo 200 palabras
- Termina indicando: "Fuente: Artículo {article_title}"

Errores comunes:
"""


def get_what_is_asked_prompt(article_title: str, article_text: str) -> str:
    """Prompt para predecir qué se pregunta sobre un artículo en exámenes."""
    return f"""Eres un especialista en diseño de preguntas de oposición basado en análisis histórico.

Artículo: {article_title}

Texto legal:
{article_text}

Tarea: Predice qué aspectos de este artículo es más probable que se pregunten en un examen de oposición.

Proporciona:
**Aspectos muy probables:**
- [aspecto 1: % estimado]
- [aspecto 2: % estimado]

**Tipos de preguntas comunes:**
- [tipo 1]
- [tipo 2]

**Trampa habitual:**
[breve descripción de cómo se intenta confundir en las opciones]

Requisitos:
- Basa tus estimados en frecuencia de preguntas similares
- Sé práctico y útil para preparación
- Máximo 150 palabras
- Termina indicando: "Fuente: Artículo {article_title}"

Análisis:
"""
