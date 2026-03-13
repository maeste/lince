---
id: LINCE-28
title: Kokoro TTS Engine Implementation
status: Done
assignee: []
created_date: '2026-03-10 14:15'
updated_date: '2026-03-10 20:12'
labels:
  - voxtts
  - engine
  - kokoro
milestone: m-9
dependencies:
  - LINCE-27
references:
  - voxcode/src/voxcode/transcriber.py
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement Kokoro TTS engine conforming to TTSEngine Protocol.

Lazy model loading with Rich spinner, auto-download via huggingface_hub on first use.
Supports --device cuda|cpu and --voice selection.
Falls back gracefully if CUDA unavailable.
Default engine for the project (82M params, top HF leaderboard).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 engines/kokoro.py implements TTSEngine Protocol
- [ ] #2 Lazy model loading with Rich spinner (auto-download via huggingface_hub on first use)
- [ ] #3 generate() returns TTSResult (numpy float32 mono array)
- [ ] #4 generate_stream() yields TTSChunk per sentence
- [ ] #5 Supports --device cuda|cpu and --voice selection
- [ ] #6 Falls back gracefully if CUDA unavailable (warning + CPU fallback)
- [ ] #7 Unit test: generate audio array from text string
<!-- AC:END -->
