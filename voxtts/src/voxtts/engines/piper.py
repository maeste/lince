"""Piper TTS engine — fast CPU-optimized TTS via ONNX runtime."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterator

import numpy as np
from rich.console import Console

from voxtts.engine import TTSChunk, TTSResult
from voxtts.engines import register_engine

logger = logging.getLogger(__name__)
console = Console()

_PIPER_DEFAULT_SAMPLE_RATE = 22050


@register_engine("piper")
class PiperEngine:
    """Piper TTS engine with lazy model loading. CPU-only via ONNX runtime."""

    def __init__(self, model: str = "en_US-lessac-medium", data_dir: str = "") -> None:
        self._model_name = model
        self._data_dir = Path(data_dir).expanduser() if data_dir else Path("~/.local/share/piper").expanduser()
        self._voice = None
        self._sample_rate: int = _PIPER_DEFAULT_SAMPLE_RATE

    @property
    def is_loaded(self) -> bool:
        return self._voice is not None

    @property
    def native_sample_rate(self) -> int:
        return self._sample_rate

    def load_model(self) -> None:
        if self._voice is not None:
            return

        try:
            from piper import PiperVoice
            from piper.download import ensure_voice_exists, find_voice, get_voices
        except ImportError as exc:
            raise ImportError(
                "piper-tts is not installed. Install it with: pip install piper-tts"
            ) from exc

        self._data_dir.mkdir(parents=True, exist_ok=True)

        with console.status("[bold green]Downloading Piper voice model..."):
            voices_info = get_voices(self._data_dir, update_voices=True)
            ensure_voice_exists(self._model_name, [self._data_dir], self._data_dir, voices_info)
            logger.info("Piper voice '%s' ready in %s", self._model_name, self._data_dir)

        with console.status("[bold green]Loading Piper TTS model..."):
            model_path, config_path = find_voice(self._model_name, [self._data_dir])
            self._voice = PiperVoice.load(str(model_path), config_path=str(config_path))
            self._sample_rate = self._voice.config.sample_rate
            logger.info(
                "Piper model loaded: voice=%s, sample_rate=%d",
                self._model_name,
                self._sample_rate,
            )

    def _ensure_model(self) -> None:
        if not self.is_loaded:
            self.load_model()

    def generate(self, text: str, language: str | None = None) -> TTSResult:
        """Generate audio for the full text as a single result."""
        self._ensure_model()

        audio_bytes = b"".join(self._voice.synthesize_stream_raw(text))

        if not audio_bytes:
            return TTSResult(audio=np.array([], dtype=np.float32), sample_rate=self._sample_rate)

        audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32767.0

        return TTSResult(audio=audio, sample_rate=self._sample_rate)

    def generate_stream(
        self, sentences: list[str], language: str | None = None
    ) -> Iterator[TTSChunk]:
        """Yield one TTSChunk per sentence for streaming playback."""
        self._ensure_model()

        for index, sentence in enumerate(sentences):
            audio_bytes = b"".join(self._voice.synthesize_stream_raw(sentence))

            if audio_bytes:
                audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32767.0
                yield TTSChunk(
                    audio=audio,
                    sample_rate=self._sample_rate,
                    sentence=sentence,
                    index=index,
                )
