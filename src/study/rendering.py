"""Rendering utilities for study content with integrated highlighting."""

from __future__ import annotations

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
    if not text or not highlights:
        return text

    # Sort highlights by position in text (longest first to handle overlaps)
    sorted_highlights = sorted(
        highlights,
        key=lambda h: len(h.get("selected_text", "")),
        reverse=True
    )

    html_text = text

    for hl in sorted_highlights:
        fragment = hl.get("selected_text", "").strip()
        if not fragment:
            continue

        color_key = hl.get("color", "yellow")
        bg_color = HIGHLIGHT_COLORS_CSS.get(color_key, "#FFEB3B")

        # Find and replace the fragment (case-insensitive, flexible whitespace)
        pattern = re.escape(fragment)
        # Replace any whitespace sequence with flexible matcher
        pattern = re.sub(r'\\s+', r'\\s+', pattern)

        replacement = f'<mark style="background-color: {bg_color}; padding: 2px 0;">{fragment}</mark>'

        # Try exact match first, then case-insensitive
        html_text = re.sub(pattern, replacement, html_text, count=1, flags=re.IGNORECASE)

    return html_text
