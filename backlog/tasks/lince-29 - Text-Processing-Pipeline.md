---
id: LINCE-29
title: Text Processing Pipeline
status: Done
assignee: []
created_date: '2026-03-10 14:15'
updated_date: '2026-03-10 20:12'
labels:
  - voxtts
  - text
  - processing
milestone: m-9
dependencies:
  - LINCE-27
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement text preprocessing pipeline for TTS input.

Sentence splitting with regex handling abbreviations, decimals, URLs.
Markdown stripping (headers, bold/italic, links, code blocks).
Language auto-detection via lingua-py returning ISO 639-1 codes.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 text.py with split_sentences() (regex-based, handles abbreviations, decimals, URLs)
- [ ] #2 strip_markdown() removes headers, bold/italic, links, code blocks
- [ ] #3 detect_language() via lingua-py, returns ISO 639-1 code
- [ ] #4 preprocess() pipeline combining strip + detect
- [ ] #5 Unit tests for each function with edge cases
<!-- AC:END -->
