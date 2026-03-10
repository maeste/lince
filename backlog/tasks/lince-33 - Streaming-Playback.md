---
id: LINCE-33
title: Streaming Playback
status: Done
assignee: []
created_date: '2026-03-10 14:16'
updated_date: '2026-03-10 20:27'
labels:
  - voxtts
  - streaming
  - playback
milestone: m-9
dependencies:
  - LINCE-31
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement sentence-by-sentence streaming playback for low-latency TTS output.

--stream flag in CLI for sentence-by-sentence playback.
play_stream() in audio.py using sounddevice OutputStream, plays chunks as they arrive.
generate_stream() in KokoroEngine yields TTSChunk per sentence.
Ctrl+C interrupts streaming playback gracefully.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 --stream flag in CLI for sentence-by-sentence playback
- [ ] #2 play_stream() in audio.py using sounddevice OutputStream, plays chunks as they arrive
- [ ] #3 generate_stream() in KokoroEngine yields TTSChunk per sentence
- [ ] #4 voxtts file.txt --play --stream plays with low perceived latency
- [ ] #5 Ctrl+C interrupts streaming playback gracefully
<!-- AC:END -->
