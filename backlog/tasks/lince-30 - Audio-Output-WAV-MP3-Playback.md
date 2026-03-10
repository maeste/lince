---
id: LINCE-30
title: Audio Output (WAV/MP3 + Playback)
status: Done
assignee: []
created_date: '2026-03-10 14:15'
updated_date: '2026-03-10 20:12'
labels:
  - voxtts
  - audio
  - output
milestone: m-9
dependencies:
  - LINCE-27
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement audio output module supporting WAV and MP3 file saving plus direct playback.

WAV via soundfile, MP3 via lameenc (192kbps default, no ffmpeg needed).
Direct playback via sounddevice with Ctrl+C graceful stop.
Format inference from output path extension or explicit -f flag.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 audio.py with save_wav() via soundfile, save_mp3() via lameenc (192kbps default)
- [ ] #2 save_audio() dispatcher based on file extension
- [ ] #3 play_audio() via sounddevice with Ctrl+C graceful stop
- [ ] #4 infer_format() from output path extension or explicit -f flag, default MP3
- [ ] #5 Unit test: save/load roundtrip for WAV and MP3
<!-- AC:END -->
