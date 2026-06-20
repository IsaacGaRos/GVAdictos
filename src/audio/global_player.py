"""TTS player — arquitectura de iframes locales con callbacks en parent.

Diseño:
- Cada iframe TTS (artículo, ley, tema) reproduce en su propio window.speechSynthesis.
  Esto garantiza que el gesto del usuario (clic) esté en el mismo browsing context
  que la síntesis de voz, evitando bloqueos de autoplay.
- Al comenzar, el iframe registra callbacks { pause, stop, getLabel, getProgress }
  en window.parent.gvaTTS._active.
- La barra de estado global lee window.parent.gvaTTS._active para mostrar estado.
- Los botones globales ⏸ ⏹ llaman a window.parent.gvaTTS._active.pause/stop().
- La velocidad se almacena en window.parent.gvaTTS.speed y se lee al hablar.
- Los saltos de línea del texto se reemplazan por espacios antes de hablar.
"""
from __future__ import annotations

import json
import streamlit as st

_SPEED_KEY = "_tts_speed"
_ITEMS_KEY = "_tts_items"
_AUTOPLAY_KEY = "_tts_autoplay"

# Inicializa el objeto gvaTTS en el parent (sin lógica de síntesis)
_INIT_ENGINE_JS = r"""
(function() {
  if (window.parent.gvaTTS) return;
  window.parent.gvaTTS = {
    speed: 1.0,
    loop: false,
    _active: null,
    toggleLoop: function() { this.loop = !this.loop; return this.loop; }
  };
})();
"""

# Lógica de síntesis local (ejecutada dentro de cada iframe)
# Requiere que la variable `items` y `safe_key` estén definidas antes.
_SPEAK_JS = r"""
var _synth = window.speechSynthesis;
var _idx = 0, _stopped = false;

function _speak() {
  if (_stopped || _idx >= _items.length) {
    var gva = window.parent.gvaTTS;
    if (gva) { gva._active = null; }
    return;
  }
  var item = _items[_idx];
  var cleanText = (item.text || '').replace(/[\n\r]+/g, ' ').replace(/\s{2,}/g, ' ').trim();
  var u = new SpeechSynthesisUtterance(cleanText);
  u.lang = 'es-ES';
  var gva = window.parent.gvaTTS;
  u.rate = (gva && gva.speed) ? gva.speed : 1.0;
  u.onend = function() {
    if (!_stopped) {
      _idx++;
      var gva2 = window.parent.gvaTTS;
      if (gva2 && gva2.loop && _idx >= _items.length) { _idx = 0; }
      setTimeout(_speak, 250);
    }
  };
  u.onerror = function() { _stopped = true; };
  _synth.speak(u);
}

function _play() {
  _stopped = false; _idx = 0; _synth.cancel();
  // Registrar callbacks en parent para control global
  var gva = window.parent.gvaTTS;
  if (gva) {
    gva._active = {
      pause: function() {
        if (_synth.paused) _synth.resume();
        else if (_synth.speaking) _synth.pause();
      },
      stop: function() { _stopped = true; _synth.cancel(); },
      getLabel: function() {
        if (_stopped) return '⏹ Detenido';
        if (!_synth.speaking && _idx >= _items.length) return '✓ Finalizado';
        return '▶ ' + (_items[_idx] ? _items[_idx].label : '');
      },
      getProgress: function() {
        return _items.length > 1 ? (_idx + 1) + '/' + _items.length : '';
      }
    };
  }
  _speak();
}
"""

_BTN_CSS = (
    "background:#313244;border:1px solid #45475a;color:#cdd6f4;"
    "padding:2px 8px;border-radius:4px;cursor:pointer;font-size:13px;"
    "font-family:system-ui,sans-serif;"
)
_BTN_HOVER_CSS = ".b:hover{background:#45475a}"


def tts_init_iframe(speed: float = 1.0) -> None:
    """Iframe oculto que inicializa window.parent.gvaTTS y actualiza la velocidad."""
    html = f"""
<script>{_INIT_ENGINE_JS}</script>
<script>
(function() {{
  var gva = window.parent.gvaTTS;
  if (gva) gva.speed = {speed};
}})();
</script>"""
    st.components.v1.html(html, height=1)


def tts_status_bar() -> None:
    """Barra de estado: muestra qué se está leyendo + botones ⏸ ⏹ 🔁."""
    html = f"""
<style>
body{{margin:0;background:transparent}}
#bar{{display:flex;align-items:center;gap:6px;padding:4px 8px;
      background:#1e1e2e;border:1px solid #313244;border-radius:6px}}
#lbl{{flex:1;font-size:11px;color:#89b4fa;overflow:hidden;
      text-overflow:ellipsis;white-space:nowrap;font-family:system-ui}}
#prg{{font-size:10px;color:#6c7086;white-space:nowrap;font-family:system-ui}}
.b{{{_BTN_CSS}}}{_BTN_HOVER_CSS}
.on{{background:#89b4fa!important;color:#1e1e2e!important}}
</style>
<div id="bar">
  <span id="lbl">&#x1F507; Sin reproducci&#xF3;n</span>
  <span id="prg"></span>
  <button class="b" id="bp" onclick="doPause()" title="Pausa/Reanudar">&#9208;</button>
  <button class="b" onclick="doStop()"           title="Parar">&#9209;</button>
  <button class="b" id="bl" onclick="doLoop()"   title="Repetir">&#x1F501;</button>
</div>
<script>
(function(){{
  function doPause(){{
    var gva=window.parent.gvaTTS;
    if(gva&&gva._active) gva._active.pause();
  }}
  function doStop(){{
    var gva=window.parent.gvaTTS;
    if(gva&&gva._active) {{ gva._active.stop(); gva._active=null; }}
    var lbl=document.getElementById('lbl');
    if(lbl) lbl.textContent='⏹ Detenido';
  }}
  function doLoop(){{
    var gva=window.parent.gvaTTS; if(!gva)return;
    var on=gva.toggleLoop();
    var bl=document.getElementById('bl');
    if(bl) bl.classList.toggle('on',on);
  }}
  function poll(){{
    var gva=window.parent.gvaTTS;
    var lbl=document.getElementById('lbl'), prg=document.getElementById('prg');
    if(gva&&gva._active){{
      if(lbl) lbl.textContent=gva._active.getLabel()||'▶ Reproduciendo';
      if(prg) prg.textContent=gva._active.getProgress()||'';
    }}
    setTimeout(poll,400);
  }}
  window.doPause=doPause; window.doStop=doStop; window.doLoop=doLoop;
  poll();
}})();
</script>"""
    st.components.v1.html(html, height=50)


def render_article_tts(items: list[dict], key: str) -> None:
    """Controles inline 🔊 ⏸ ⏹ para un artículo. Síntesis en el iframe local."""
    items_json = json.dumps(items, ensure_ascii=False)
    safe_key = key.replace("-", "_").replace(".", "_")
    html = f"""
<script>{_INIT_ENGINE_JS}</script>
<script type="application/json" id="d_{safe_key}">{items_json}</script>
<style>
body{{margin:0;background:transparent}}
.b{{{_BTN_CSS}}}{_BTN_HOVER_CSS}
#w{{display:flex;gap:3px;align-items:center;padding:2px}}
</style>
<div id="w">
  <button class="b" onclick="_play()" title="Reproducir">&#x1F50A;</button>
  <button class="b" id="pbtn" onclick="_pauseLocal()" title="Pausa">&#9208;</button>
  <button class="b" onclick="_stopLocal()" title="Parar">&#9209;</button>
</div>
<script>
var _items = JSON.parse(document.getElementById('d_{safe_key}').textContent);
{_SPEAK_JS}
function _pauseLocal(){{
  if(_synth.paused)_synth.resume(); else if(_synth.speaking)_synth.pause();
  var pb=document.getElementById('pbtn');
  if(pb) pb.textContent=_synth.paused?'▶':'⏸';
}}
function _stopLocal(){{
  _stopped=true; _synth.cancel();
  var pb=document.getElementById('pbtn'); if(pb) pb.textContent='⏸';
}}
</script>"""
    st.components.v1.html(html, height=36)


def render_tts_button_iframe(items: list[dict], label: str = "🔊", key: str = "") -> None:
    """Botón TTS para leyes/temas. Síntesis en el iframe local. Sin rerun de Streamlit."""
    items_json = json.dumps(items, ensure_ascii=False)
    safe_key = (key or label).replace("-", "_").replace(".", "_").replace(" ", "_")
    html = f"""
<script>{_INIT_ENGINE_JS}</script>
<script type="application/json" id="d_{safe_key}">{items_json}</script>
<style>
body{{margin:0;background:transparent}}
.b{{{_BTN_CSS}}}{_BTN_HOVER_CSS}
</style>
<button class="b" onclick="_play()" title="Reproducir">{label}</button>
<script>
var _items = JSON.parse(document.getElementById('d_{safe_key}').textContent);
{_SPEAK_JS}
</script>"""
    st.components.v1.html(html, height=36)


def render_global_player() -> None:
    """Slider de velocidad + init iframe + barra de estado. Llamar al inicio de Estudiar."""
    col_speed, col_bar = st.columns([1, 4])
    with col_speed:
        speed = st.slider(
            "Velocidad",
            0.5, 2.0,
            float(st.session_state.get(_SPEED_KEY, 1.0)),
            0.25,
            key=_SPEED_KEY,
            format="%.2f×",
        )
        tts_init_iframe(speed=speed)  # 1px, dentro de la columna de velocidad
    with col_bar:
        tts_status_bar()


def tts_button(
    items: list[dict],
    label: str = "🔊",
    key: str = "",
    help_text: str = "Reproducir",
    use_container_width: bool = False,
) -> None:
    """Botón Streamlit nativo — ruta legacy, sigue siendo usable."""
    if st.button(label, key=key, help=help_text, use_container_width=use_container_width):
        st.session_state[_ITEMS_KEY] = items
        st.session_state[_AUTOPLAY_KEY] = True
        st.rerun()
