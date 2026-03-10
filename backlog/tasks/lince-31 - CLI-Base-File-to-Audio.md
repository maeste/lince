---
id: LINCE-31
title: CLI Base + File-to-Audio
status: Done
assignee: []
created_date: '2026-03-10 14:15'
updated_date: '2026-03-10 20:20'
labels:
  - voxtts
  - cli
milestone: m-9
dependencies:
  - LINCE-28
  - LINCE-29
  - LINCE-30
references:
  - voxcode/src/voxcode/cli.py
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement CLI with argparse and orchestration for file-to-audio conversion.

CLI arguments: input_file, -o, -f, --play, --engine, --device, --language, --voice, --config, --list-voices, --list-devices.
Orchestration: parse args → load config → get text → preprocess → generate → save/play.
If neither -o nor --play specified, defaults to --play.
Format inferred from -o extension, overridable with -f.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 cli.py with argparse: input_file, -o, -f, --play, --engine, --device, --language, --voice, --config, --list-voices, --list-devices
- [ ] #2 Orchestration: parse args → load config → get text → preprocess → generate → save/play
- [ ] #3 voxtts file.txt -o output.mp3 produces valid MP3
- [ ] #4 voxtts file.txt -o output.wav produces valid WAV
- [ ] #5 voxtts file.txt --play plays audio through speakers
- [ ] #6 If neither -o nor --play specified, defaults to --play
- [ ] #7 Format inferred from -o extension, overridable with -f
<!-- AC:END -->
