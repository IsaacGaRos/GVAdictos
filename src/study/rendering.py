"""Rendering utilities for study content with integrated highlighting."""

from __future__ import annotations

import html as html_module
import re


HIGHLIGHT_COLORS_CSS = {
    "yellow": "#FFEB3B",
    "green": "#4CAF50",
    "blue": "#2196F3",
    "pink": "#FF69B4",
    "purple": "#9C27B0",
    "red": "#F44336",
}


def render_text_with_highlights(
    text: str,
    highlights: list[dict],
) -> str:
    """Render text with integrated HTML highlighting.

    Args:
        text: The full article text
        highlights: List of dicts with 'selected_text' and 'color' keys

    Returns:
        HTML string with highlights applied
    """
    if not text:
        return text

    if not highlights:
        return text

    # Sort highlights by position in text (longest first to handle overlaps)
    sorted_highlights = sorted(
        highlights,
        key=lambda h: len(h.get("selected_text", "")),
        reverse=True
    )

    result = text

    for hl in sorted_highlights:
        fragment = hl.get("selected_text", "").strip()
        if not fragment or len(fragment) < 2:
            continue

        color_key = hl.get("color", "yellow")
        bg_color = HIGHLIGHT_COLORS_CSS.get(color_key, "#FFEB3B")

        # Simple string replacement: look for exact fragment
        # First try exact case, then case-insensitive
        safe_fragment = html_module.escape(fragment)
        replacement = f'<mark style="background-color: {bg_color}; padding: 2px 4px; border-radius: 2px;">{safe_fragment}</mark>'

        if fragment in result:
            # Exact match exists
            result = result.replace(fragment, replacement, 1)
        else:
            # Try case-insensitive with regex
            pattern = re.escape(fragment)
            result = re.sub(pattern, replacement, result, count=1, flags=re.IGNORECASE)

    return result
