"""Global floating TTS player injected once per page render.

Exposes a window-level JS API (`window.gvaTTS`) that all article play buttons call.
Uses Web Speech API — zero cost, zero backend.
"""
from __future__ import annotations

import json
import streamlit as st


PLAYER_CSS = """
<style>
#gva-player {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: #181825;
    border-top: 1px solid #313244;
    padding: 10px 24px;
    z-index: 9999;
    display: flex;
    align-items: center;
    gap: 14px;
    font-size: 13px;
    color: #cdd6f4;
    box-shadow: 0 -2px 12px rgba(0,0,0,.4);
}
#gva-player .gva-btn {
    background: #313244;
    border: 1px solid #45475a;
    color: #cdd6f4;
    padding: 5px 11px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 14px;
    transition: background .15s;
}
#gva-player .gva-btn:hover { background: #45475a; }
#gva-player .gva-btn.active { background: #89b4fa; color: #1e1e2e; }
#gva-now-playing { flex: 1; min-width: 120px; color: #89b4fa; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
#gva-progress { color: #6c7086; font-size: 11px; min-width: 50px; }
#gva-speed {
    background: #313244;
    border: 1px solid #45475a;
    color: #cdd6f4;
    padding: 4px 6px;
    border-radius: 5px;
    cursor: pointer;
    font-size: 12px;
}
/* Push Streamlit content above the fixed bar */
section[data-testid="stMain"] > div { padding-bottom: 70px !important; }
</style>
"""

PLAYER_HTML = """
<div id="gva-player">
  <span id="gva-now-playing">— Sin reproducción —</span>
  <span id="gva-progress"></span>
  <button class="gva-btn" id="gva-btn-play"  onclick="gvaTTS.play()">▶</button>
  <button class="gva-btn" id="gva-btn-pause" onclick="gvaTTS.pause()">⏸</button>
  <button class="gva-btn" id="gva-btn-stop"  onclick="gvaTTS.stop()">⏹</button>
  <label style="font-size:11px;color:#6c7086;">Vel.</label>
  <select id="gva-speed" onchange="gvaTTS.onSpeedChange()">
    <option value="0.75">0.75×</option>
    <option value="1.0" selected>1.0×</option>
    <option value="1.25">1.25×</option>
    <option value="1.5">1.5×</option>
    <option value="1.75">1.75×</option>
    <option value="2.0">2.0×</option>
  </select>
</div>
"""

PLAYER_JS = """
<script>
(function() {
  // Only define once
  if (window.gvaTTS) return;

  const synth = window.speechSynthesis;

  window.gvaTTS = {
    items: [],
    index: 0,
    stopped: false,
    paused: false,

    load: function(items) {
      this.items = items;
      this.index = 0;
      this.stopped = false;
    },

    play: function() {
      if (this.paused && synth.paused) {
        synth.resume();
        this.paused = false;
        this._setLabel();
        return;
      }
      this.stopped = false;
      this.paused = false;
      synth.cancel();
      this._next();
    },

    pause: function() {
      if (synth.speaking && !synth.paused) {
        synth.pause();
        this.paused = true;
        document.getElementById('gva-now-playing').textContent = '⏸ ' + (this.items[this.index]?.label || '');
      }
    },

    stop: function() {
      this.stopped = true;
      this.paused = false;
      synth.cancel();
      document.getElementById('gva-now-playing').textContent = '— Sin reproducción —';
      document.getElementById('gva-progress').textContent = '';
    },

    onSpeedChange: function() {
      // Speed is read dynamically in _next — nothing to do here.
    },

    _speed: function() {
      return parseFloat(document.getElementById('gva-speed')?.value || '1.0');
    },

    _setLabel: function() {
      const item = this.items[this.index];
      if (!item) return;
      const el = document.getElementById('gva-now-playing');
      if (el) el.textContent = '▶ ' + item.label;
      const prog = document.getElementById('gva-progress');
      if (prog) prog.textContent = (this.index + 1) + '/' + this.items.length;
    },

    _next: function() {
      if (this.stopped || this.index >= this.items.length) {
        if (this.index >= this.items.length) {
          const el = document.getElementById('gva-now-playing');
          if (el) el.textContent = '✓ Finalizado';
          const prog = document.getElementById('gva-progress');
          if (prog) prog.textContent = '';
        }
        return;
      }

      const item = this.items[this.index];
      this._setLabel();

      const utt = new SpeechSynthesisUtterance(item.text);
      utt.rate = this._speed();
      utt.lang = 'es-ES';
      const voices = synth.getVoices();
      if (voices.length) utt.voice = voices[0];

      const self = this;
      utt.onend = function() {
        if (!self.stopped && !self.paused) {
          self.index++;
          setTimeout(function() { self._next(); }, 300);
        }
      };
      utt.onerror = function(e) {
        const el = document.getElementById('gva-now-playing');
        if (el) el.textContent = '⚠ Error: ' + e.error;
      };

      synth.speak(utt);
    }
  };
})();
</script>
"""


def inject_global_player() -> None:
    """Inject the floating TTS player into the Streamlit page once per session."""
    if st.session_state.get("_gva_player_injected"):
        return
    st.session_state["_gva_player_injected"] = True
    st.markdown(PLAYER_CSS + PLAYER_HTML + PLAYER_JS, unsafe_allow_html=True)


def play_items_button(
    items: list[dict],
    label: str = "▶",
    key: str = "",
    style: str = "",
) -> None:
    """Render a small HTML button that loads items into the global player and plays.

    Args:
        items: list of {"text": str, "label": str}
        label: button display label
        key: unique HTML id suffix
        style: extra inline CSS
    """
    items_json = json.dumps(items, ensure_ascii=False)
    default_style = (
        "background:transparent;border:none;color:#89b4fa;cursor:pointer;"
        "font-size:16px;padding:2px 6px;border-radius:4px;"
    )
    btn_html = (
        f'<button id="play_{key}" '
        f'style="{default_style}{style}" '
        f'onclick=\'window.gvaTTS.load({items_json}); window.gvaTTS.play();\'>'
        f"{label}</button>"
    )
    st.markdown(btn_html, unsafe_allow_html=True)
