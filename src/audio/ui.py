"""UI integration for TTS (Streamlit).

MVP: Uses browser Web Speech API for cost-free playback.
"""

from __future__ import annotations

import sqlite3
import base64
import streamlit as st

from src.audio.service import TTSService, TTSServiceError
from src.core.db import connect


@st.cache_resource
def get_tts_service() -> TTSService | None:
    """Get or initialize TTSService."""
    try:
        conn = connect()
        service = TTSService(conn)
        return service
    except Exception as e:
        st.warning(f"Error initializing TTS service: {e}")
        return None


def render_tts_player(article_id: int, article_title: str, article_text: str) -> None:
    """Render TTS player for an article (Ola D4)."""
    service = get_tts_service()
    if not service:
        return

    with st.expander("Escuchar (TTS - Ola D4)", expanded=False):
        st.markdown("**Reproductor de texto a voz**")

        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            voice = col1.selectbox(
                "Voz",
                [None, "spanish", "spanish-es"],
                format_func=lambda x: "Automática" if x is None else x,
                key=f"tts_voice_{article_id}",
            )
        with col2:
            speed = col2.slider(
                "Velocidad",
                min_value=0.5,
                max_value=2.0,
                value=1.0,
                step=0.1,
                key=f"tts_speed_{article_id}",
            )
        with col3:
            st.write("")
            estimated_duration = service.estimate_duration(article_text, speed)
            st.caption(f"~{estimated_duration:.0f}s")

        if st.button(
            "Reproducir",
            key=f"tts_play_{article_id}",
            help="Reproduce el texto del artículo en el navegador (sin coste)",
        ):
            # Prepare audio metadata
            audio_data = service.get_or_create_audio(
                scope_type="article",
                scope_id=article_id,
                text=article_text,
                voice=voice,
                speed=speed,
            )

            st.success("Iniciando reproducción...")

            # Generate JavaScript for Web Speech API
            js_code = _generate_web_speech_js(
                article_text,
                voice=voice,
                speed=speed,
                article_title=article_title,
            )

            # Render using components.html
            st.components.v1.html(
                js_code,
                height=100,
                scrolling=False,
            )


def _generate_web_speech_js(
    text: str,
    voice: str | None = None,
    speed: float = 1.0,
    article_title: str = "Article",
) -> str:
    """Generate HTML/JS for Web Speech API player."""
    # Escape text for JavaScript
    safe_text = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")

    voice_selection = f"voices.find(v => v.lang.includes('{voice}')) || voices[0]" if voice else "voices[0]"

    html = f"""
    <div id="tts-player" style="padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
        <p><strong>Reproduciendo:</strong> {article_title}</p>
        <div id="controls">
            <button id="playBtn" onclick="startSpeech()" style="padding: 8px 16px; margin: 5px; cursor: pointer;">
                ▶ Reproducir
            </button>
            <button id="pauseBtn" onclick="pauseSpeech()" style="padding: 8px 16px; margin: 5px; cursor: pointer;">
                ⏸ Pausar
            </button>
            <button id="stopBtn" onclick="stopSpeech()" style="padding: 8px 16px; margin: 5px; cursor: pointer;">
                ⏹ Detener
            </button>
        </div>
        <p id="status" style="font-size: 12px; color: #666; margin-top: 10px;"></p>
    </div>

    <script>
    const synth = window.speechSynthesis;
    let utterance = null;

    function startSpeech() {{
        if (synth.paused) {{
            synth.resume();
            return;
        }}

        // Cancel any ongoing speech
        synth.cancel();

        utterance = new SpeechSynthesisUtterance("{safe_text}");
        utterance.rate = {speed};
        utterance.lang = "es-ES";

        const voices = synth.getVoices();
        if (voices.length > 0) {{
            utterance.voice = {voice_selection};
        }}

        utterance.onstart = () => {{
            document.getElementById('status').textContent = 'Reproduciendo...';
        }};

        utterance.onend = () => {{
            document.getElementById('status').textContent = 'Reproducción finalizada';
        }};

        utterance.onerror = (event) => {{
            document.getElementById('status').textContent = 'Error: ' + event.error;
        }};

        synth.speak(utterance);
    }}

    function pauseSpeech() {{
        if (synth.speaking && !synth.paused) {{
            synth.pause();
            document.getElementById('status').textContent = 'En pausa';
        }}
    }}

    function stopSpeech() {{
        synth.cancel();
        document.getElementById('status').textContent = 'Detenido';
    }}

    // Ensure voices are loaded
    if (synth.onvoiceschanged !== undefined) {{
        synth.onvoiceschanged = () => {{}};
    }}
    </script>
    """
    return html
