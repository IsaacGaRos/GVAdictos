"""TTS player via window.parent — same-origin iframe access.

Architecture:
- Speech synthesis runs on the Streamlit app (parent) window via window.parent.gvaTTS.
- st.components.v1.html iframes are same-origin (localhost) and CAN access window.parent.
- tts_init_iframe(): creates gvaTTS on parent window; loads items if autoplay.
- tts_status_bar(): polling status + pause/stop/loop controls via parent.gvaTTS.
- render_article_tts(): per-article 🔊 ⏸ ⏹ iframe (direct call, no Streamlit rerun).
- tts_button(): Streamlit native button for large playlists (law/topic) — rerun approach.
"""
from __future__ import annotations

import json
import streamlit as st

_SPEED_KEY = "_tts_speed"
_ITEMS_KEY = "_tts_items"
_AUTOPLAY_KEY = "_tts_autoplay"

# JS engine definition — injected once on the parent window
_ENGINE_JS = """
(function() {
  if (window.parent.gvaTTS) return;
  var synth = window.parent.speechSynthesis;
  window.parent.gvaTTS = {
    synth: synth,
    items: [], idx: 0, stopped: true, loop: false, speed: 1.0,
    label: '🔇 Sin reproducción', progress: '',

    load: function(items) {
      this.items = items; this.idx = 0; this.stopped = false;
    },
    play: function() {
      this.stopped = false; this.synth.cancel(); this._next();
    },
    pause: function() {
      var s = this.synth;
      if (s.paused) s.resume(); else if (s.speaking) s.pause();
    },
    stop: function() {
      this.stopped = true; this.synth.cancel();
      this.label = '⏹ Detenido'; this.progress = '';
    },
    toggleLoop: function() { this.loop = !this.loop; return this.loop; },
    _next: function() {
      var self = this;
      if (self.stopped || self.idx >= self.items.length) {
        if (self.idx >= self.items.length) {
          if (self.loop) { self.idx = 0; self._next(); return; }
          self.label = '✓ Finalizado'; self.progress = '';
        }
        return;
      }
      var item = self.items[self.idx];
      self.label = '▶ ' + item.label;
      self.progress = (self.idx + 1) + '/' + self.items.length;
      var u = new window.parent.SpeechSynthesisUtterance(item.text);
      u.rate = self.speed; u.lang = 'es-ES';
      u.onend = function() {
        if (!self.stopped) { self.idx++; setTimeout(function(){ self._next(); }, 250); }
      };
      u.onerror = function(e) { self.label = '⚠ ' + e.error; };
      self.synth.speak(u);
    }
  };
})();
"""

_BTN_STYLE = (
    "background:#313244;border:1px solid #45475a;color:#cdd6f4;"
    "padding:2px 8px;border-radius:4px;cursor:pointer;font-size:13px;"
    "font-family:system-ui,sans-serif;"
)
_BTN_HOVER = ".b:hover{background:#45475a!important}"


def tts_init_iframe(items: list | None = None, autoplay: bool = False, speed: float = 1.0) -> None:
    """Hidden iframe that initialises gvaTTS on the parent window.

    On every render, it updates the speed. If autoplay=True and items are given,
    it loads and plays them immediately (no Streamlit rerun needed after this call).
    """
    cfg = json.dumps(
        {"items": items or [], "autoplay": autoplay, "speed": speed},
        ensure_ascii=False,
    )
    html = f"""
<script>{_ENGINE_JS}</script>
<script type="application/json" id="cfg">{cfg}</script>
<script>
(function(){{
  var cfg = JSON.parse(document.getElementById('cfg').textContent);
  var gva = window.parent.gvaTTS;
  gva.speed = cfg.speed;
  if (cfg.autoplay && cfg.items.length > 0) {{
    gva.load(cfg.items);
    gva.play();
  }}
}})();
</script>"""
    st.components.v1.html(html, height=0)


def tts_status_bar() -> None:
    """Polling status bar + pause / stop / loop controls."""
    html = f"""
<style>
body{{margin:0;background:transparent}}
#bar{{display:flex;align-items:center;gap:6px;padding:4px 8px;
      background:#1e1e2e;border:1px solid #313244;border-radius:6px}}
#lbl{{flex:1;font-size:11px;color:#89b4fa;overflow:hidden;
      text-overflow:ellipsis;white-space:nowrap;font-family:system-ui}}
#prg{{font-size:10px;color:#6c7086;white-space:nowrap;font-family:system-ui}}
.b{{{_BTN_STYLE}}}{_BTN_HOVER}
.on{{background:#89b4fa!important;color:#1e1e2e!important}}
</style>
<div id="bar">
  <span id="lbl">🔇 Sin reproducción</span>
  <span id="prg"></span>
  <button class="b" id="bp" onclick="doPause()" title="Pausa/Reanudar">⏸</button>
  <button class="b" onclick="doStop()"           title="Parar">⏹</button>
  <button class="b" id="bl" onclick="doLoop()"   title="Repetir">🔁</button>
</div>
<script>
(function(){{
  function doPause(){{
    var gva=window.parent.gvaTTS; if(!gva)return; gva.pause();
    var bp=document.getElementById('bp');
    if(bp) bp.textContent=window.parent.speechSynthesis.paused?'▶':'⏸';
  }}
  function doStop(){{
    var gva=window.parent.gvaTTS; if(!gva)return; gva.stop();
    var bp=document.getElementById('bp'); if(bp) bp.textContent='⏸';
  }}
  function doLoop(){{
    var gva=window.parent.gvaTTS; if(!gva)return;
    var on=gva.toggleLoop();
    var bl=document.getElementById('bl');
    if(bl) bl.classList.toggle('on',on);
  }}
  function poll(){{
    var gva=window.parent.gvaTTS;
    if(gva){{
      var lbl=document.getElementById('lbl'), prg=document.getElementById('prg');
      if(lbl) lbl.textContent=gva.label||'🔇 Sin reproducción';
      if(prg) prg.textContent=gva.progress||'';
    }}
    setTimeout(poll,400);
  }}
  window.doPause=doPause; window.doStop=doStop; window.doLoop=doLoop;
  poll();
}})();
</script>"""
    st.components.v1.html(html, height=50)


def render_article_tts(items: list[dict], key: str) -> None:
    """Inline 🔊 ⏸ ⏹ controls for a single article. No Streamlit rerun on play."""
    items_json = json.dumps(items, ensure_ascii=False)
    safe_key = key.replace("-", "_").replace(".", "_")
    html = f"""
<script type="application/json" id="d_{safe_key}">{items_json}</script>
<style>
body{{margin:0;background:transparent}}
.b{{{_BTN_STYLE}}}{_BTN_HOVER}
#w{{display:flex;gap:3px;align-items:center;padding:2px}}
</style>
<div id="w">
  <button class="b" onclick="pl()" title="Reproducir">🔊</button>
  <button class="b" id="bp_{safe_key}" onclick="pa()" title="Pausa">⏸</button>
  <button class="b" onclick="st_()" title="Parar">⏹</button>
</div>
<script>
(function(){{
  var items=JSON.parse(document.getElementById('d_{safe_key}').textContent);
  var bp=document.getElementById('bp_{safe_key}');
  function pl(){{
    var gva=window.parent.gvaTTS;
    if(!gva){{alert('TTS no listo. Recarga la página.');return;}}
    gva.load(items); gva.play();
    if(bp) bp.textContent='⏸';
  }}
  function pa(){{
    var gva=window.parent.gvaTTS; if(!gva)return; gva.pause();
    if(bp) bp.textContent=window.parent.speechSynthesis.paused?'▶':'⏸';
  }}
  function st_(){{
    var gva=window.parent.gvaTTS; if(gva) gva.stop();
    if(bp) bp.textContent='⏸';
  }}
  window['pl_{safe_key}']=pl; window['pa_{safe_key}']=pa; window['st_{safe_key}']=st_;
}})();
</script>"""
    st.components.v1.html(html, height=36)


def render_global_player() -> None:
    """Speed slider + init iframe + status bar. Call once at top of study section."""
    items = st.session_state.get(_ITEMS_KEY, [])
    autoplay = bool(st.session_state.get(_AUTOPLAY_KEY, False))
    if autoplay:
        st.session_state[_AUTOPLAY_KEY] = False

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

    tts_init_iframe(items=items if autoplay else None, autoplay=autoplay, speed=speed)

    with col_bar:
        tts_status_bar()


def tts_button(
    items: list[dict],
    label: str = "🔊",
    key: str = "",
    help_text: str = "Reproducir",
    use_container_width: bool = False,
) -> None:
    """Streamlit button — queues items via session_state for large playlists (law/topic)."""
    if st.button(label, key=key, help=help_text, use_container_width=use_container_width):
        st.session_state[_ITEMS_KEY] = items
        st.session_state[_AUTOPLAY_KEY] = True
        st.rerun()
