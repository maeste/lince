"""CLI entry point and orchestration."""

import argparse
import sys

from rich.console import Console

from voxtts import __version__
from voxtts.audio import play_audio, play_stream, save_audio
from voxtts.config import load_config
from voxtts.engine import create_engine
from voxtts.engines import load_engines
from voxtts.reader import get_input_text
from voxtts.text import preprocess, split_sentences

console = Console(stderr=True)


def _list_devices():
    """Print available audio output devices."""
    import sounddevice as sd

    console.print("[bold]Available audio output devices:[/bold]")
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        if dev["max_output_channels"] > 0:
            marker = " (default)" if dev["name"] == sd.query_devices(kind="output")["name"] else ""
            console.print(f"  {i}: {dev['name']}{marker}")


def _list_voices(engine_name: str):
    """Print available voices for the given engine."""
    load_engines()
    from voxtts.engines import ENGINE_REGISTRY

    if engine_name not in ENGINE_REGISTRY:
        console.print(f"[red]Unknown engine: {engine_name}[/red]")
        return

    if engine_name == "kokoro":
        console.print("[bold]Available Kokoro voices:[/bold]")
        voices = [
            ("af_heart", "American Female (Heart) — default"),
            ("af_bella", "American Female (Bella)"),
            ("af_nicole", "American Female (Nicole)"),
            ("af_sarah", "American Female (Sarah)"),
            ("af_sky", "American Female (Sky)"),
            ("am_adam", "American Male (Adam)"),
            ("am_michael", "American Male (Michael)"),
            ("bf_emma", "British Female (Emma)"),
            ("bf_isabella", "British Female (Isabella)"),
            ("bm_george", "British Male (George)"),
            ("bm_lewis", "British Male (Lewis)"),
        ]
        for voice_id, desc in voices:
            console.print(f"  {voice_id:20s} {desc}")
    elif engine_name == "piper":
        console.print("[bold]Piper voices:[/bold]")
        console.print("  See https://rhasspy.github.io/piper-samples/ for available models.")
        console.print("  Set via --voice or config [piper] model = \"model_name\"")
    else:
        console.print(f"Voice listing not available for engine: {engine_name}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="voxtts",
        description="Text-to-Speech with local GPU/CPU engines",
    )
    parser.add_argument("input_file", nargs="?", help="Text file to convert")
    parser.add_argument("-o", "--output", help="Output audio file path")
    parser.add_argument(
        "-f", "--format", choices=["mp3", "wav"], help="Output format (default: from -o extension, or mp3)"
    )
    parser.add_argument("--play", action="store_true", help="Play audio through speakers")
    parser.add_argument("--stream", action="store_true", help="Stream playback sentence-by-sentence")
    parser.add_argument("--clipboard", action="store_true", help="Read text from clipboard")
    parser.add_argument("--pane", action="store_true", help="Read text from active tmux/zellij pane")
    parser.add_argument(
        "--pane-target", default=None,
        help="Target pane direction: left, right, up, down, next, previous (default: from config)",
    )
    parser.add_argument("--engine", default=None, help="TTS engine (kokoro, piper)")
    parser.add_argument("--device", default=None, help="Compute device (cuda, cpu)")
    parser.add_argument("--language", default=None, help="Language override (en, it, es...)")
    parser.add_argument("--voice", default=None, help="Voice selection")
    parser.add_argument("--config", default=None, help="Config file path")
    parser.add_argument("--list-voices", action="store_true", help="List available voices")
    parser.add_argument("--list-devices", action="store_true", help="List audio output devices")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # --list-devices: show available audio output devices
    if args.list_devices:
        _list_devices()
        sys.exit(0)

    # --list-voices: show available voices for the selected engine
    if args.list_voices:
        config = load_config(args.config)
        engine_name = args.engine or config.general.engine
        _list_voices(engine_name)
        sys.exit(0)

    # If no input source and no list command, show help
    has_input = args.input_file or args.clipboard or args.pane
    if not has_input and sys.stdin.isatty():
        parser.print_help()
        sys.exit(0)

    try:
        # 1. Load configuration and apply CLI overrides
        config = load_config(args.config)

        engine_name = args.engine or config.general.engine
        device = args.device or config.kokoro.device
        voice = args.voice or config.kokoro.voice

        # 2. Register available engines
        load_engines()

        # 3. Acquire input text
        pane_target = args.pane_target
        if args.pane and not pane_target:
            backend = config.multiplexer.backend
            if backend == "auto":
                from voxtts.multiplexer import detect_multiplexer
                try:
                    backend = detect_multiplexer()
                except RuntimeError:
                    backend = ""
            if backend == "zellij":
                pane_target = config.zellij.target_pane
            elif backend == "tmux":
                pane_target = config.tmux.target_pane

        text = get_input_text(
            input_file=args.input_file,
            clipboard=args.clipboard,
            pane=args.pane,
            pane_target=pane_target or "",
            backend=config.multiplexer.backend,
        )

        if not text.strip():
            console.print("[red]Error: input text is empty.[/red]")
            sys.exit(1)

        # 4. Preprocess text and detect language
        cleaned_text, detected_language = preprocess(text)
        language = args.language if args.language else detected_language

        # 5. Create engine
        engine = create_engine(engine_name, device=device, voice=voice)

        # 6. Output: save to file and/or play
        should_play = args.play or not args.output

        if args.stream and should_play:
            # Streaming mode: play sentence-by-sentence
            sentences = split_sentences(cleaned_text)
            if args.output:
                # Save full audio first, then stream playback
                result = engine.generate(cleaned_text, language=language)
                save_audio(result.audio, result.sample_rate, args.output, format=args.format)
                console.print(f"[green]Saved:[/green] {args.output}")
                play_stream(engine.generate_stream(sentences, language=language))
            else:
                play_stream(engine.generate_stream(sentences, language=language))
        else:
            # Non-streaming mode
            result = engine.generate(cleaned_text, language=language)
            if args.output:
                save_audio(result.audio, result.sample_rate, args.output, format=args.format)
                console.print(f"[green]Saved:[/green] {args.output}")
                if args.play:
                    play_audio(result.audio, result.sample_rate)
            else:
                play_audio(result.audio, result.sample_rate)

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        sys.exit(130)
    except FileNotFoundError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        sys.exit(1)
    except ValueError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        sys.exit(1)
    except ImportError as exc:
        console.print(f"[red]Error: Missing dependency: {exc}[/red]")
        if "kokoro" in str(exc):
            console.print("[yellow]Try: pip install kokoro, or use --engine piper[/yellow]")
        elif "piper" in str(exc):
            console.print("[yellow]Try: pip install voxtts[piper], or use --engine kokoro[/yellow]")
        sys.exit(1)
    except RuntimeError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        sys.exit(1)
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
