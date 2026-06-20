"""Global TTS player using Streamlit session_state + st.components.v1.html().

Flow:
  1. tts_button() is a native Streamlit button. On click, items go into session_state
     and the page reruns.
  2. render_global_player() detects new items and renders an html iframe that
     auto-plays via Web Speech API (zero cost, browser-native).
  3. Pause / Stop / Repeat controls live inside the iframe — no Streamlit rerun needed.
  4. The speed slider lives outside the iframe (Streamlit slider) and is shared
     across all play requests.
"""
from __future__ import annotations

import json
import streamlit as st

_SPEED_KEY = "_tts_speed"
_ITEMS_KEY = "_tts_items"
_AUTOPLAY_KEY = "_tts_autoplay"


def tts_button(
    items: list[dict],
    label: str = "🔊",
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
    """Render the shared TTS player bar.

    Shows a speed slider on the left and a player component on the right.
    The player component includes pause / stop / repeat controls rendered
    inside its own iframe so they work without Streamlit reruns.
    """
    items = st.session_state.get(_ITEMS_KEY, [])
    autoplay = bool(st.session_state.get(_AUTOPLAY_KEY, False))
    if autoplay:
        st.session_state[_AUTOPLAY_KEY] = False

    col_speed, col_player = st.columns([1, 4])
    with col_speed:
        st.slider(
            "Velocidad",
            min_value=0.5,
            max_value=2.0,
            value=float(st.session_state.get(_SPEED_KEY, 1.0)),
            step=0.25,
            key=_SPEED_KEY,
            format="%.2f×",
        )
    with col_player:
        speed = float(st.session_state.get(_SPEED_KEY, 1.0))
        _render_player_iframe(items, speed=speed, autoplay=autoplay)


def _render_player_iframe(
    items: list[dict],
    speed: float = 1.0,
    autoplay: bool = False,
) -> None:
    """Render the player iframe with built-in pause/stop/repeat controls."""
    cfg = json.dumps({"items": items, "speed": speed, "autoplay": autoplay}, ensure_ascii=False)

    html = f"""
<script type="application/json" id="tts-cfg">{cfg}</script>
<style>
  body {{ margin:0; background:transparent; font-family:system-ui,sans-serif; }}
  #bar {{ display:flex; align-items:center; gap:6px; padding:4px 6px;
          background:#1e1e2e; border:1px solid #313244; border-radius:6px; }}
  #tts-lbl {{ flex:1; font-size:11px; color:#89b4fa; white-space:nowrap;
              overflow:hidden; text-overflow:ellipsis; min-width:0; }}
  #tts-prg {{ font-size:10px; color:#6c7086; white-space:nowrap; }}
  .ctrl {{ background:#313244; border:1px solid #45475a; color:#cdd6f4;
           padding:2px 7px; border-radius:4px; cursor:pointer; font-size:13px; }}
  .ctrl:hover {{ background:#45475a; }}
  .ctrl.on {{ background:#89b4fa; color:#1e1e2e; }}
</style>
<div id="bar">
  <span id="tts-lbl">🔇 Sin reproducción</span>
  <span id="tts-prg"></span>
  <button class="ctrl" id="btn-pause" onclick="doPause()" title="Pausar/Reanudar">⏸</button>
  <button class="ctrl" id="btn-stop"  onclick="doStop()"  title="Parar">⏹</button>
  <button class="ctrl" id="btn-loop"  onclick="doLoop()"  title="Repetir">🔁</button>
</div>
<script>
(function(){{
  var cfg = JSON.parse(document.getElementById('tts-cfg').textContent);
  var synth = window.speechSynthesis;
  var idx = 0, stopped = false, loop = false;

  function setLabel(txt) {{
    var el = document.getElementById('tts-lbl');
    if (el) el.textContent = txt;
  }}
  function setProg(txt) {{
    var el = document.getElementById('tts-prg');
    if (el) el.textContent = txt;
  }}

  function speak() {{
    if (stopped) return;
    if (idx >= cfg.items.length) {{
      if (loop) {{ idx = 0; speak(); return; }}
      setLabel('✓ Finalizado');
      setProg('');
      return;
    }}
    var item = cfg.items[idx];
    var u = new SpeechSynthesisUtterance(item.text);
    u.rate = cfg.speed; u.lang = 'es-ES';
    setLabel('▶ ' + item.label);
    setProg((idx+1) + '/' + cfg.items.length);
    u.onend = function() {{ if (!stopped) {{ idx++; setTimeout(speak, 250); }} }};
    u.onerror = function(e) {{ setLabel('⚠ ' + e.error); }};
    synth.speak(u);
  }}

  function doPause() {{
    var btn = document.getElementById('btn-pause');
    if (synth.paused) {{
      synth.resume();
      if (btn) btn.textContent = '⏸';
    }} else if (synth.speaking) {{
      synth.pause();
      if (btn) btn.textContent = '▶';
    }}
  }}

  function doStop() {{
    stopped = true; synth.cancel();
    setLabel('⏹ Detenido'); setProg('');
    var btn = document.getElementById('btn-pause');
    if (btn) btn.textContent = '⏸';
  }}

  function doLoop() {{
    loop = !loop;
    var btn = document.getElementById('btn-loop');
    if (btn) {{ btn.classList.toggle('on', loop); btn.title = loop ? 'Repetir: ON' : 'Repetir'; }}
  }}

  if (cfg.autoplay && cfg.items.length > 0) {{ synth.cancel(); stopped = false; idx = 0; speak(); }}
}})();
</script>"""

    # height 52 fits the bar comfortably
    st.components.v1.html(html, height=52)
