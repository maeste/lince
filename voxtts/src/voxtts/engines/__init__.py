"""TTS engine registry."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from voxtts.engine import TTSEngine

# Engine registry: name -> class
# Engines register themselves when imported
ENGINE_REGISTRY: dict[str, type[TTSEngine]] = {}


def register_engine(name: str):
    """Decorator to register a TTS engine class."""
    def decorator(cls):
        ENGINE_REGISTRY[name] = cls
        return cls
    return decorator


def load_engines():
    """Import all engine modules to trigger registration."""
    try:
        import voxtts.engines.kokoro  # noqa: F401
    except ImportError:
        pass

    try:
        import voxtts.engines.piper  # noqa: F401
    except ImportError:
        pass
