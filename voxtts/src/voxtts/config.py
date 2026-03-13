"""Configuration loading and defaults."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GeneralConfig:
    engine: str = "kokoro"
    language: str = "auto"
    output_format: str = "mp3"


@dataclass
class KokoroConfig:
    device: str = "cuda"
    voice: str = "af_heart"


@dataclass
class PiperConfig:
    model: str = "en_US-lessac-medium"
    data_dir: str = ""


@dataclass
class AudioConfig:
    device: int | None = None  # sounddevice output device index, None = system default


@dataclass
class PlaybackConfig:
    stream: bool = False


@dataclass
class MultiplexerConfig:
    backend: str = "auto"  # "auto" | "tmux" | "zellij"


@dataclass
class TmuxConfig:
    target_pane: str = ""


@dataclass
class ZellijConfig:
    target_pane: str = ""


@dataclass
class VoxTTSConfig:
    general: GeneralConfig = field(default_factory=GeneralConfig)
    kokoro: KokoroConfig = field(default_factory=KokoroConfig)
    piper: PiperConfig = field(default_factory=PiperConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    playback: PlaybackConfig = field(default_factory=PlaybackConfig)
    multiplexer: MultiplexerConfig = field(default_factory=MultiplexerConfig)
    tmux: TmuxConfig = field(default_factory=TmuxConfig)
    zellij: ZellijConfig = field(default_factory=ZellijConfig)


def _apply_section(config_obj, data: dict):
    for key, value in data.items():
        if hasattr(config_obj, key):
            setattr(config_obj, key, value)


def load_config(path: str | None = None) -> VoxTTSConfig:
    config = VoxTTSConfig()

    if path is None:
        candidates = [
            Path.cwd() / "config.toml",
            Path.home() / ".config" / "voxtts" / "config.toml",
        ]
        for candidate in candidates:
            if candidate.exists():
                path = str(candidate)
                break

    if path and Path(path).exists():
        with open(path, "rb") as f:
            data = tomllib.load(f)

        section_map = {
            "general": config.general,
            "kokoro": config.kokoro,
            "piper": config.piper,
            "audio": config.audio,
            "playback": config.playback,
            "multiplexer": config.multiplexer,
            "tmux": config.tmux,
            "zellij": config.zellij,
        }
        for section_name, config_obj in section_map.items():
            if section_name in data:
                _apply_section(config_obj, data[section_name])

    return config
