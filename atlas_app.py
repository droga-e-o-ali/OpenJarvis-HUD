"""Janela nativa do A.T.L.A.S para Windows.

Mantém os serviços locais separados da interface para facilitar uma futura
migração para um aplicativo com instalador completo.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
import webview
from faster_whisper import WhisperModel

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
LOCAL = Path(os.environ["LOCALAPPDATA"])
CREATE_NO_WINDOW = 0x08000000


class AtlasVoice:
    """Captura e transcreve localmente, sem depender do Web Speech do navegador."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._stream = None
        self._chunks: list[np.ndarray] = []
        self._model = None

    def start_recording(self) -> bool:
        with self._lock:
            if self._stream is not None:
                return True
            self._chunks = []

            def capture(indata, _frames, _time, status) -> None:
                if not status:
                    self._chunks.append(indata.copy())

            self._stream = sd.InputStream(
                samplerate=16000, channels=1, dtype="float32", callback=capture
            )
            self._stream.start()
        return True

    def stop_recording(self) -> str:
        with self._lock:
            stream, self._stream = self._stream, None
            chunks, self._chunks = self._chunks, []
        if stream is not None:
            stream.stop()
            stream.close()
        if not chunks:
            return ""
        audio = np.concatenate(chunks, axis=0).reshape(-1)
        if len(audio) < 3200:
            return ""
        if self._model is None:
            self._model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, _info = self._model.transcribe(
            audio, language="pt", beam_size=3, vad_filter=True
        )
        return " ".join(segment.text.strip() for segment in segments).strip()


def listening(port: int) -> bool:
    with socket.socket() as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def launch(command: list[str], cwd: Path | None = None, env: dict | None = None) -> None:
    subprocess.Popen(command, cwd=cwd, env=env, creationflags=CREATE_NO_WINDOW)


def wait_for(port: int, seconds: int = 12) -> bool:
    for _ in range(seconds * 5):
        if listening(port):
            return True
        time.sleep(0.2)
    return False


def start_services() -> None:
    ollama = LOCAL / "Programs" / "Ollama" / "ollama.exe"
    python = LOCAL / "Programs" / "Python" / "Python313" / "python.exe"
    uv = LOCAL / "Microsoft" / "WinGet" / "Links" / "uv.exe"
    source = LOCAL / "OpenJarvis" / "src"
    if not ollama.exists() or not python.exists() or not uv.exists() or not source.exists():
        raise RuntimeError("A instalação local do OpenJarvis não foi encontrada.")
    if not listening(11434):
        launch([str(ollama), "serve"])
        wait_for(11434)
    if not listening(8000):
        env = os.environ.copy()
        env["OPENJARVIS_CORS_ORIGINS"] = "http://127.0.0.1:8787"
        launch([str(uv), "run", "jarvis", "serve", "--host", "127.0.0.1", "--port", "8000", "--engine", "ollama", "--model", "qwen3.5:4b", "--agent", "simple"], source, env)
        wait_for(8000)
    if not listening(8787):
        launch([str(python), str(ROOT / "atlas_server.py")], ROOT)
        wait_for(8787)


if __name__ == "__main__":
    try:
        start_services()
        window = webview.create_window("A.T.L.A.S CORE", "http://127.0.0.1:8787", js_api=AtlasVoice(), width=1440, height=900, min_size=(1000, 680), background_color="#01050c")
        webview.start()
    except Exception as exc:
        webview.create_window("A.T.L.A.S — erro", html=f"<pre style='padding:24px'>{exc}</pre>")
        webview.start()
