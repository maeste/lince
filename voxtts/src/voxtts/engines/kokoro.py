"""Kokoro TTS engine — lazy-loaded neural TTS via kokoro + huggingface_hub."""

from __future__ import annotations

import logging
import warnings
from typing import Iterator

import numpy as np
from rich.console import Console

from voxtts.engine import TTSChunk, TTSResult
from voxtts.engines import register_engine

logger = logging.getLogger(__name__)
console = Console()

_KOKORO_SAMPLE_RATE = 24000


@register_engine("kokoro")
class KokoroEngine:
    """Kokoro TTS engine with lazy model loading and CUDA fallback."""

    def __init__(self, device: str = "cuda", voice: str = "af_heart") -> None:
        self._requested_device = device
        self._device = device
        self._voice = voice
        self._pipeline = None

    @property
    def is_loaded(self) -> bool:
        return self._pipeline is not None

    @property
    def native_sample_rate(self) -> int:
        return _KOKORO_SAMPLE_RATE

    def load_model(self) -> None:
        if self._pipeline is not None:
            return

        import kokoro

        with console.status("[bold green]Loading Kokoro TTS model..."):
            try:
                self._pipeline = kokoro.KPipeline(lang_code="a", device=self._device)
                logger.info("Kokoro model loaded on device=%s", self._device)
            except RuntimeError as exc:
                if self._device != "cpu":
                    console.print(
                        f"[yellow]WARNING: Failed to load Kokoro on {self._device}: {exc}. "
                        "Falling back to CPU.[/yellow]"
                    )
                    warnings.warn(
                        f"CUDA unavailable for Kokoro ({exc}), falling back to CPU.",
                        RuntimeWarning,
                        stacklevel=2,
                    )
                    self._device = "cpu"
                    self._pipeline = kokoro.KPipeline(lang_code="a", device="cpu")
                    logger.info("Kokoro model loaded on fallback device=cpu")
                else:
                    raise

    def _ensure_model(self) -> None:
        if not self.is_loaded:
            self.load_model()

    def generate(self, text: str, language: str | None = None) -> TTSResult:
        """Generate audio for the full text, concatenating all sentence chunks."""
        self._ensure_model()

        audio_parts: list[np.ndarray] = []
        for _graphemes, _phonemes, audio_tensor in self._pipeline(
            text, voice=self._voice
        ):
            if audio_tensor is not None:
                chunk_np = audio_tensor.cpu().numpy().astype(np.float32).flatten()
                audio_parts.append(chunk_np)

        if not audio_parts:
            return TTSResult(
                audio=np.array([], dtype=np.float32), sample_rate=_KOKORO_SAMPLE_RATE
            )

        return TTSResult(
            audio=np.concatenate(audio_parts), sample_rate=_KOKORO_SAMPLE_RATE
        )

    def generate_stream(
        self, sentences: list[str], language: str | None = None
    ) -> Iterator[TTSChunk]:
        """Yield one TTSChunk per sentence for streaming playback."""
        self._ensure_model()

        for index, sentence in enumerate(sentences):
            audio_parts: list[np.ndarray] = []
            for _graphemes, _phonemes, audio_tensor in self._pipeline(
                sentence, voice=self._voice
            ):
                if audio_tensor is not None:
                    chunk_np = audio_tensor.cpu().numpy().astype(np.float32).flatten()
                    audio_parts.append(chunk_np)

            if audio_parts:
                yield TTSChunk(
                    audio=np.concatenate(audio_parts),
                    sample_rate=_KOKORO_SAMPLE_RATE,
                    sentence=sentence,
                    index=index,
                )
