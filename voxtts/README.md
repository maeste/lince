# VoxTTS

Text-to-Speech for Linux with local GPU/CPU engines. Convert text files, clipboard content, or terminal pane captures into natural-sounding audio — all processing happens on your machine.

VoxTTS is the output counterpart to [VoxCode](../voxcode/) (speech-to-text). Together they close the voice loop: you speak to Claude Code via VoxCode, and Claude's output can be read back to you via VoxTTS.

## How it works

```
Text → Preprocessing → Kokoro/Piper TTS (local) → Audio → Speakers / MP3 / WAV
```

VoxTTS reads text from multiple sources (files, clipboard, stdin, tmux/Zellij panes), auto-detects the language, and synthesizes speech using a local neural TTS engine. Output goes to speakers, an audio file, or both.

## Prerequisites

- **Linux** (tested on Fedora 43)
- **Python 3.11+** (3.12 recommended; 3.14 has compatibility issues with torch)
- **[uv](https://github.com/astral-sh/uv)** (Python package manager)
- **NVIDIA GPU** (recommended for Kokoro engine) or CPU-only (slower but works)

## Installation

```bash
cd voxtts
uv sync
```

First run downloads the Kokoro model (~300 MB) from HuggingFace automatically.

**CPU-only installation** works out of the box — Kokoro falls back to CPU if CUDA is unavailable:

```bash
uv run voxtts file.txt --play --device cpu
```

### Optional: Piper engine

For a faster, CPU-optimized alternative:

```bash
uv pip install voxtts[piper]
uv run voxtts file.txt --play --engine piper
```

## Quick start

```bash
# Read a file aloud
uv run voxtts notes.txt --play

# Save to MP3
uv run voxtts article.txt -o article.mp3

# Save to WAV
uv run voxtts document.txt -o document.wav

# Pipe from another command
echo "Hello, world!" | uv run voxtts --play

# Read clipboard content
uv run voxtts --clipboard --play

# Read active tmux/Zellij pane
uv run voxtts --pane -o pane_content.mp3
```

## Input sources

VoxTTS accepts text from multiple sources:

| Source | Flag | Example |
|---|---|---|
| File | positional arg | `voxtts readme.txt --play` |
| Clipboard | `--clipboard` | `voxtts --clipboard --play` |
| tmux/Zellij pane | `--pane` | `voxtts --pane -o pane.mp3` |
| Stdin pipe | (automatic) | `cat file.txt \| voxtts --play` |

Priority order: file > clipboard > pane > stdin.

**Clipboard** uses `wl-paste` (Wayland) or `xclip` (X11) — install whichever matches your display server.

**Pane capture** auto-detects tmux or Zellij from environment variables and captures the active pane content.

## Output modes

| Mode | Flags | Behavior |
|---|---|---|
| Play (default) | `--play` or no flags | Play through speakers |
| Save to file | `-o path.mp3` | Save as MP3 or WAV |
| Save + play | `-o path.mp3 --play` | Save file, then play |
| Streaming | `--play --stream` | Play sentence-by-sentence (lower latency) |

If neither `-o` nor `--play` is specified, VoxTTS defaults to `--play`.

**Streaming mode** (`--stream`) splits text into sentences and plays each one as soon as it's synthesized, reducing perceived latency for long texts.

## TTS Engines

### Kokoro (default)

[Kokoro](https://huggingface.co/hexgrad/Kokoro-82M) is a neural TTS model with 82M parameters. It produces natural, expressive speech and tops the HuggingFace TTS leaderboard.

- **Quality**: High (natural prosody, expressive)
- **Speed**: Fast on GPU, usable on CPU
- **Sample rate**: 24 kHz
- **Languages**: English (American/British), with experimental multilingual support
- **Model size**: ~300 MB (auto-downloaded on first use)

Available voices (see `--list-voices`):

| Voice ID | Description |
|---|---|
| `af_heart` | American Female (Heart) — default |
| `af_bella` | American Female (Bella) |
| `af_nicole` | American Female (Nicole) |
| `af_sarah` | American Female (Sarah) |
| `af_sky` | American Female (Sky) |
| `am_adam` | American Male (Adam) |
| `am_michael` | American Male (Michael) |
| `bf_emma` | British Female (Emma) |
| `bf_isabella` | British Female (Isabella) |
| `bm_george` | British Male (George) |
| `bm_lewis` | British Male (Lewis) |

### Piper (fallback)

[Piper](https://github.com/rhasspy/piper) is a fast, CPU-optimized TTS using ONNX runtime. It's ideal when GPU is unavailable or when speed matters more than naturalness.

- **Quality**: Good (clear, intelligible)
- **Speed**: Very fast, even on CPU
- **Languages**: 30+ languages with many voice options
- **Model size**: Varies by voice (typically 15-75 MB)

Install as optional dependency: `uv pip install voxtts[piper]`

Browse voices at [rhasspy.github.io/piper-samples](https://rhasspy.github.io/piper-samples/).

## Text preprocessing

VoxTTS automatically preprocesses input text before synthesis:

- **Markdown stripping**: Removes headers, bold/italic, links, code blocks, images
- **Language detection**: Auto-detects language via [lingua-py](https://github.com/pemistahl/lingua-py) (override with `--language`)
- **Sentence splitting**: Splits text into sentences for streaming, handling abbreviations (Mr., Dr., etc.), decimals, URLs, and ellipsis

## Configuration

VoxTTS works with sensible defaults. Create a config file only if you want to change something:

```bash
cp config.example.toml config.toml
```

Config file search order:
1. `./config.toml` (current directory)
2. `~/.config/voxtts/config.toml`
3. Built-in defaults

### Common settings

**Use CPU instead of GPU:**

```toml
[kokoro]
device = "cpu"
```

**Change default voice:**

```toml
[kokoro]
voice = "am_adam"
```

**Use Piper as default engine:**

```toml
[general]
engine = "piper"

[piper]
model = "en_US-lessac-medium"
```

**Enable streaming by default:**

```toml
[playback]
stream = true
```

**Set specific audio output device:**

```toml
[audio]
device = 0    # find yours with: voxtts --list-devices
```

## CLI reference

```
voxtts [input_file]           # text file (positional, optional)
  -o, --output PATH           # save audio to file
  -f, --format mp3|wav        # output format (default: from -o extension, or mp3)
  --play                      # play through speakers
  --stream                    # sentence-by-sentence playback (low latency)
  --clipboard                 # read from system clipboard
  --pane                      # read from active tmux/zellij pane
  --engine kokoro|piper       # TTS engine
  --device cuda|cpu           # compute device
  --language LANG             # language override (en, it, es...)
  --voice VOICE               # voice selection
  --config PATH               # config file path
  --list-voices               # list available voices
  --list-devices              # list audio output devices
  --version                   # show version
```

## Troubleshooting

### First run is slow

The first run downloads the Kokoro model (~300 MB). Subsequent runs load from cache (~3-5 seconds on GPU, ~10-15 seconds on CPU).

```bash
# Models are cached here:
ls ~/.cache/huggingface/hub/
```

### CUDA not available

VoxTTS automatically falls back to CPU with a warning. To silence the warning, set the device explicitly:

```bash
uv run voxtts file.txt --play --device cpu
```

Or in `config.toml`:

```toml
[kokoro]
device = "cpu"
```

### No clipboard tool found

Install the appropriate clipboard tool for your display server:

```bash
# Wayland
sudo dnf install wl-clipboard     # Fedora
sudo apt install wl-clipboard      # Ubuntu

# X11
sudo dnf install xclip            # Fedora
sudo apt install xclip             # Ubuntu
```

### Audio playback issues

List available output devices and check which one to use:

```bash
uv run voxtts --list-devices
```

Set a specific device in `config.toml`:

```toml
[audio]
device = 0
```

## Project structure

```
voxtts/
├── pyproject.toml           # Project config and dependencies
├── config.example.toml      # Example configuration
├── README.md                # This file
└── src/voxtts/
    ├── __init__.py           # Version
    ├── __main__.py           # python -m voxtts
    ├── cli.py                # CLI entry point and orchestration
    ├── config.py             # TOML config loading
    ├── engine.py             # TTSEngine protocol, result types, factory
    ├── engines/
    │   ├── __init__.py       # Engine registry
    │   ├── kokoro.py         # Kokoro TTS engine
    │   └── piper.py          # Piper TTS engine
    ├── text.py               # Sentence splitting, markdown strip, language detect
    ├── audio.py              # WAV/MP3 saving, playback, streaming
    ├── reader.py             # Input sources (file, clipboard, stdin, pane)
    └── multiplexer.py        # tmux/Zellij pane capture
```
