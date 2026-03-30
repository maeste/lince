---
title: VoxTTS v0.1.0
status: planned
---

# VoxTTS v0.1.0

Text-to-Speech module for the lince project. Complementary to voxcode (STT), voxtts converts text to audio with support for file input, clipboard, tmux/zellij pane capture, and direct playback. Multi-engine architecture (Kokoro TTS primary, Piper TTS fallback), local GPU+CPU execution, natural voice quality.

## Goals
- Complete TTS pipeline: text → preprocessing → synthesis → audio output
- Multi-engine support with Protocol-based plugin architecture
- Multiple input sources: file, clipboard, stdin, tmux/zellij pane
- Multiple output modes: WAV, MP3, direct playback, streaming playback
- Auto language detection with lingua-py
- CUDA GPU acceleration with CPU fallback

## Tasks
- LINCE-27: Project Skeleton + Config System
- LINCE-28: Kokoro TTS Engine Implementation
- LINCE-29: Text Processing Pipeline
- LINCE-30: Audio Output (WAV/MP3 + Playback)
- LINCE-31: CLI Base + File-to-Audio
- LINCE-32: Input Sources (clipboard, stdin, pane)
- LINCE-33: Streaming Playback
- LINCE-34: Piper TTS Engine (Fallback)
- LINCE-35: Polish + Error Handling

## Dependency Graph
```
LINCE-27 (Skeleton) ─┬─→ LINCE-28 (Kokoro) ──┐
                      ├─→ LINCE-29 (Text) ────┤
                      ├─→ LINCE-30 (Audio) ───┼─→ LINCE-31 (CLI) ─┬─→ LINCE-32 (Input Sources)
                      └─→ LINCE-34 (Piper) ───┤                   ├─→ LINCE-33 (Streaming)
                                               │                   │
                                               └───────────────────┴─→ LINCE-35 (Polish)
```
