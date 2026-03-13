"""Audio saving (WAV/MP3) and playback utilities."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from voxtts.engine import TTSChunk

import numpy as np


SUPPORTED_FORMATS = {"wav", "mp3"}


def infer_format(output_path: str | None = None, explicit_format: str | None = None) -> str:
    """Infer audio format from explicit format, file extension, or default to mp3.

    Args:
        output_path: Optional file path to extract extension from.
        explicit_format: Optional explicit format string (e.g. "wav", "mp3").

    Returns:
        Lowercase format string.

    Raises:
        ValueError: If the inferred format is not supported.
    """
    if explicit_format is not None:
        fmt = explicit_format.lower().lstrip(".")
        if fmt not in SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format '{fmt}'. Supported: {', '.join(sorted(SUPPORTED_FORMATS))}")
        return fmt

    if output_path is not None:
        _, ext = os.path.splitext(output_path)
        if ext:
            fmt = ext.lower().lstrip(".")
            if fmt not in SUPPORTED_FORMATS:
                raise ValueError(f"Unsupported format '{fmt}'. Supported: {', '.join(sorted(SUPPORTED_FORMATS))}")
            return fmt

    return "mp3"


def save_wav(audio: np.ndarray, sample_rate: int, path: str) -> None:
    """Save audio as a WAV file using soundfile.

    Args:
        audio: Float32 mono audio array with values in [-1.0, 1.0].
        sample_rate: Sample rate in Hz.
        path: Output file path.
    """
    import soundfile as sf

    sf.write(path, audio, sample_rate)


def save_mp3(audio: np.ndarray, sample_rate: int, path: str, bitrate: int = 192) -> None:
    """Save audio as an MP3 file using lameenc.

    Args:
        audio: Float32 mono audio array with values in [-1.0, 1.0].
        sample_rate: Sample rate in Hz.
        path: Output file path.
        bitrate: MP3 bitrate in kbps (default 192).
    """
    import lameenc

    pcm = (audio * 32767).astype(np.int16)
    encoder = lameenc.Encoder()
    encoder.set_bit_rate(bitrate)
    encoder.set_in_sample_rate(sample_rate)
    encoder.set_channels(1)
    encoder.set_quality(2)  # 2 = high quality
    mp3_data = encoder.encode(pcm.tobytes())
    mp3_data += encoder.flush()
    with open(path, "wb") as f:
        f.write(mp3_data)


def save_audio(
    audio: np.ndarray,
    sample_rate: int,
    path: str,
    format: str | None = None,
) -> None:
    """Save audio to a file, dispatching to the appropriate encoder.

    The format is determined by the explicit ``format`` argument if provided,
    otherwise by the file extension of ``path``.

    Args:
        audio: Float32 mono audio array with values in [-1.0, 1.0].
        sample_rate: Sample rate in Hz.
        path: Output file path.
        format: Optional explicit format ("wav" or "mp3"). Inferred from
            ``path`` extension when not provided.

    Raises:
        ValueError: If the format cannot be inferred or is unsupported.
    """
    fmt = infer_format(output_path=path, explicit_format=format)
    if fmt == "wav":
        save_wav(audio, sample_rate, path)
    elif fmt == "mp3":
        save_mp3(audio, sample_rate, path)
    else:
        raise ValueError(f"Unsupported format '{fmt}'. Supported: {', '.join(sorted(SUPPORTED_FORMATS))}")


def play_audio(audio: np.ndarray, sample_rate: int) -> None:
    """Play audio through the default output device, blocking until done.

    Handles Ctrl+C gracefully by stopping playback immediately.

    Args:
        audio: Float32 mono audio array with values in [-1.0, 1.0].
        sample_rate: Sample rate in Hz.
    """
    import sounddevice as sd

    try:
        sd.play(audio, sample_rate)
        sd.wait()
    except KeyboardInterrupt:
        sd.stop()


def play_stream(chunks: Iterator[TTSChunk]) -> None:
    """Play audio chunks as they arrive for low-latency streaming playback.

    Each chunk is played immediately via sounddevice, blocking until that chunk
    finishes before playing the next one. Ctrl+C stops playback gracefully.
    """
    import sounddevice as sd

    try:
        for chunk in chunks:
            sd.play(chunk.audio, chunk.sample_rate)
            sd.wait()
    except KeyboardInterrupt:
        sd.stop()
