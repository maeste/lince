---
id: LINCE-34
title: Piper TTS Engine (Fallback)
status: Done
assignee: []
created_date: '2026-03-10 14:16'
updated_date: '2026-03-10 20:20'
labels:
  - voxtts
  - engine
  - piper
milestone: m-9
dependencies:
  - LINCE-27
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement Piper TTS as fallback engine, CPU-optimized with ONNX runtime.

Optional dependency via pip install voxtts[piper].
Lazy model loading, auto-download ONNX models.
CPU-optimized (ONNX runtime), fast inference.
Full TTSEngine Protocol compliance.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 engines/piper.py implements TTSEngine Protocol
- [ ] #2 Optional dependency via pip install voxtts[piper]
- [ ] #3 Lazy model loading, auto-download ONNX models
- [ ] #4 CPU-optimized (ONNX runtime)
- [ ] #5 voxtts file.txt --engine piper --play works
- [ ] #6 generate() and generate_stream() produce valid audio
<!-- AC:END -->
