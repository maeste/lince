"""TTS engine protocol, result types, and factory."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Protocol

import numpy as np


@dataclass
class TTSResult:
    audio: np.ndarray  # float32 mono
    sample_rate: int


@dataclass
class TTSChunk:
    audio: np.ndarray  # float32 mono
    sample_rate: int
    sentence: str
    index: int


class TTSEngine(Protocol):
    def load_model(self) -> None: ...

    @property
    def is_loaded(self) -> bool: ...

    def generate(self, text: str, language: str | None = None) -> TTSResult: ...

    def generate_stream(
        self, sentences: list[str], language: str | None = None
    ) -> Iterator[TTSChunk]: ...

    @property
    def native_sample_rate(self) -> int: ...


def create_engine(engine_name: str, **kwargs) -> TTSEngine:
    """Create a TTS engine by name."""
    from voxtts.engines import ENGINE_REGISTRY

    if engine_name not in ENGINE_REGISTRY:
        available = ", ".join(sorted(ENGINE_REGISTRY.keys()))
        raise ValueError(f"Unknown engine '{engine_name}'. Available: {available}")

    engine_class = ENGINE_REGISTRY[engine_name]
    return engine_class(**kwargs)
