"""UI integration for TTS (Streamlit).

MVP: Uses browser Web Speech API for cost-free playback.
"""

from __future__ import annotations

import sqlite3
import base64
import streamlit as st

from src.audio.service import TTSService, TTSServiceError
from src.core.db import connect


def get_tts_service() -> TTSService | None:
    """Get a fresh TTSService.

    No caching: a cached connection would be bound to the thread that created
    it and Streamlit reruns can land on a different thread (sqlite3 raises
    'objects created in a thread can only be used in that same thread').
    """
    try:
        return TTSService(connect())
    except Exception as e:
        st.warning(f"Error initializing TTS service: {e}")
        return None


def render_tts_button(
    key: str,
    text: str,
    label: str = "🔊 Escuchar",
    speed: float = 1.0,
    help_text: str = "Lee el texto en voz alta en el navegador (sin coste)",
    prefix: str = "",
) -> None:
    """Render expandable TTS player with play/pause/stop and loop controls.

    Cost-free: uses the browser Web Speech API. Reads only `text`, ignoring `prefix`.
    """
    if not text or not text.strip():
        return

    with st.expander(label, expanded=False):
        st.caption(help_text)

        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            current_speed = st.slider(
                "Velocidad",
                min_value=0.5,
                max_value=2.0,
                value=speed,
                step=0.1,
                key=f"tts_speed_{key}",
            )
        with col2:
            loop_enabled = st.checkbox(
                "Repetir ♻️",
                value=False,
                key=f"tts_loop_{key}",
                help="Repetir indefinidamente",
            )
        with col3:
            st.write("")

        col_play, col_pause, col_stop = st.columns(3)
        with col_play:
            play_btn = st.button("▶ Play", key=f"tts_play_{key}", use_container_width=True)
        with col_pause:
            pause_btn = st.button("⏸ Pause", key=f"tts_pause_{key}", use_container_width=True)
        with col_stop:
            stop_btn = st.button("⏹ Stop", key=f"tts_stop_{key}", use_container_width=True)

        if play_btn or pause_btn or stop_btn:
            js_code = _generate_web_speech_js(
                text=text,
                voice=None,
                speed=current_speed,
                article_title=label,
                loop=loop_enabled,
                autostart=play_btn,
            )
            st.components.v1.html(js_code, height=60, scrolling=False)


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
    loop: bool = False,
    autostart: bool = False,
) -> str:
    """Generate HTML/JS for Web Speech API player with loop support.

    Args:
        text: content to read (body text only)
        voice: optional voice identifier
        speed: playback speed (0.5-2.0)
        article_title: label for display
        loop: if True, repeats indefinitely
        autostart: if True, begin playback immediately
    """
    safe_text = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    voice_selection = f"voices.find(v => v.lang.includes('{voice}')) || voices[0]" if voice else "voices[0]"
    loop_check = "true" if loop else "false"

    autostart_js = (
        "if (synth.getVoices().length > 0) { startSpeech(); }"
        " else { synth.onvoiceschanged = () => { startSpeech(); }; }"
        if autostart else ""
    )

    html = f"""
    <div id="tts-player" style="padding: 8px; font-size: 12px;">
        <p id="status" style="color: #666; margin: 3px 0; font-size: 11px;">Listo</p>
    </div>

    <script>
    const synth = window.speechSynthesis;
    let utterance = null;
    let loopEnabled = {loop_check};
    let shouldStop = false;

    function playText() {{
        if (shouldStop) return;

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
            if (shouldStop) {{
                document.getElementById('status').textContent = 'Detenido';
                return;
            }}
            if (loopEnabled) {{
                setTimeout(() => {{
                    playText();
                }}, 500);
            }} else {{
                document.getElementById('status').textContent = 'Finalizado';
            }}
        }};

        utterance.onerror = (event) => {{
            document.getElementById('status').textContent = 'Error: ' + event.error;
        }};

        synth.speak(utterance);
    }}

    function startSpeech() {{
        if (synth.paused) {{
            synth.resume();
            return;
        }}
        shouldStop = false;
        synth.cancel();
        playText();
    }}

    function pauseSpeech() {{
        if (synth.speaking && !synth.paused) {{
            synth.pause();
            document.getElementById('status').textContent = 'Pausado';
        }}
    }}

    function stopSpeech() {{
        shouldStop = true;
        synth.cancel();
        document.getElementById('status').textContent = 'Detenido';
    }}

    // Auto-start if requested
    {autostart_js}
    </script>
    """
    return html
