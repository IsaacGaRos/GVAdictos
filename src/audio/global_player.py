"""Global TTS player using Streamlit session_state + st.components.v1.html().

Flow:
  1. tts_button() renders a native Streamlit button.
  2. On click, items are stored in session_state and the page reruns.
  3. render_global_player() detects new items and renders an html component
     that auto-plays via Web Speech API (zero cost, browser-native).
  4. Speed slider is shared across all requests via session_state.
"""
from __future__ import annotations

import json
import streamlit as st

_SPEED_KEY = "_tts_speed"
_ITEMS_KEY = "_tts_items"
_AUTOPLAY_KEY = "_tts_autoplay"


def tts_button(
    items: list[dict],
    label: str = "▶",
    key: str = "",
    help_text: str = "Reproducir en voz alta",
    use_container_width: bool = False,
) -> None:
    """Render a Streamlit button that queues items for TTS playback on next rerun."""
    if st.button(label, key=key, help=help_text, use_container_width=use_container_width):
        st.session_state[_ITEMS_KEY] = items
        st.session_state[_AUTOPLAY_KEY] = True
        st.rerun()


def render_global_player() -> None:
    """Render the shared TTS status bar. Call once per study section render.

    Shows a speed slider (shared across all play requests) and current playback status.
    When tts_button() queues items, auto-plays on the next render cycle.
    """
    items = st.session_state.get(_ITEMS_KEY, [])
    autoplay = bool(st.session_state.get(_AUTOPLAY_KEY, False))
    if autoplay:
        st.session_state[_AUTOPLAY_KEY] = False  # consume the flag

    with st.container(border=False):
        col_speed, col_status = st.columns([1, 3])
        with col_speed:
            st.slider(
                "Velocidad TTS",
                min_value=0.5,
                max_value=2.0,
                value=float(st.session_state.get(_SPEED_KEY, 1.0)),
                step=0.25,
                key=_SPEED_KEY,
                format="%.2f×",
                label_visibility="collapsed",
            )
        with col_status:
            if items:
                n = len(items)
                lbl = items[0].get("label", "—")
                extra = f" + {n - 1} fragmentos más" if n > 1 else ""
                st.caption(f"🔊 Reproduciendo: **{lbl}**{extra}")
            else:
                st.caption("🔇 Sin reproducción activa")

        if items:
            speed = float(st.session_state.get(_SPEED_KEY, 1.0))
            _render_speech_html(items, speed=speed, autoplay=autoplay)


def _render_speech_html(items: list[dict], speed: float = 1.0, autoplay: bool = False) -> None:
    """Render an iframe component that speaks items via Web Speech API."""
    cfg = json.dumps({"items": items, "speed": speed, "autoplay": autoplay}, ensure_ascii=False)
    html = f"""
<script type="application/json" id="tts-cfg">{cfg}</script>
<div id="tts-bar" style="padding:4px 10px;font-size:11px;color:#cdd6f4;
     background:#1e1e2e;border-radius:4px;border:1px solid #313244;display:flex;align-items:center;gap:10px;">
  <span id="tts-lbl">⏳ Listo</span>
  <span id="tts-prg" style="color:#6c7086;font-size:10px;"></span>
</div>
<script>
(function(){{
  var cfg = JSON.parse(document.getElementById('tts-cfg').textContent);
  var synth = window.speechSynthesis;
  var idx = 0;
  function speak() {{
    if (idx >= cfg.items.length) {{
      var lbl = document.getElementById('tts-lbl');
      if (lbl) lbl.textContent = '✓ Finalizado';
      var prg = document.getElementById('tts-prg');
      if (prg) prg.textContent = '';
      return;
    }}
    var item = cfg.items[idx];
    var u = new SpeechSynthesisUtterance(item.text);
    u.rate = cfg.speed; u.lang = 'es-ES';
    var lbl = document.getElementById('tts-lbl');
    var prg = document.getElementById('tts-prg');
    if (lbl) lbl.textContent = '▶ ' + item.label;
    if (prg) prg.textContent = (idx+1) + '/' + cfg.items.length;
    u.onend = function() {{ idx++; setTimeout(speak, 250); }};
    u.onerror = function(e) {{ if (lbl) lbl.textContent = '⚠ ' + e.error; }};
    synth.speak(u);
  }}
  if (cfg.autoplay) {{ synth.cancel(); speak(); }}
}})();
</script>"""
    st.components.v1.html(html, height=36)
