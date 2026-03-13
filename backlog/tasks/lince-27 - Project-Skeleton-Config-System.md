---
id: LINCE-27
title: Project Skeleton + Config System
status: Done
assignee: []
created_date: '2026-03-10 14:15'
updated_date: '2026-03-10 14:35'
labels:
  - voxtts
  - skeleton
  - config
milestone: m-9
dependencies: []
references:
  - voxcode/src/voxcode/config.py
  - voxcode/pyproject.toml
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Setup voxtts/ project with src layout, pyproject.toml, config system, and engine protocol.

Project structure: voxtts/src/voxtts/ with __init__.py, __main__.py, config.py, engine.py, engines/__init__.py
Config system: TOML-based dataclass config following voxcode/src/voxcode/config.py pattern
Engine protocol: TTSEngine Protocol with TTSResult/TTSChunk dataclasses and engine factory
Dependencies: kokoro, soundfile, sounddevice, numpy, rich, lameenc, lingua-language-detector
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 voxtts/ directory exists with src layout (src/voxtts/)
- [ ] #2 pyproject.toml with hatchling build and all dependencies
- [ ] #3 __init__.py with version, __main__.py entry point
- [ ] #4 config.py with TOML-based dataclass config (GeneralConfig, KokoroConfig, PiperConfig, AudioConfig, PlaybackConfig, MultiplexerConfig)
- [ ] #5 load_config() with same pattern as voxcode/src/voxcode/config.py
- [ ] #6 config.example.toml with all sections documented
- [ ] #7 engine.py with TTSEngine Protocol, TTSResult/TTSChunk dataclasses, engine factory
- [ ] #8 engines/__init__.py with engine registry
- [ ] #9 uv sync && uv run voxtts --help works
<!-- AC:END -->
