"""Text preprocessing pipeline: sentence splitting, markdown stripping, and language detection."""

from __future__ import annotations

import re

from lingua import Language, LanguageDetectorBuilder

# ---------------------------------------------------------------------------
# Module-level language detector (built once, reused across calls)
# ---------------------------------------------------------------------------
_detector = LanguageDetectorBuilder.from_all_languages().build()

# ---------------------------------------------------------------------------
# Abbreviations that should NOT trigger sentence splits
# ---------------------------------------------------------------------------
_ABBREVIATIONS = frozenset(
    {
        "Mr",
        "Mrs",
        "Ms",
        "Dr",
        "Prof",
        "Inc",
        "Ltd",
        "Corp",
        "St",
        "Jr",
        "Sr",
        "vs",
        "etc",
        "approx",
        "dept",
        "est",
        "govt",
        "no",
        "vol",
    }
)

_ABBREVIATION_PAIRS = frozenset({"i.e", "e.g"})

# ---------------------------------------------------------------------------
# Compiled regex patterns
# ---------------------------------------------------------------------------

# Placeholder tokens used during sentence splitting
_URL_PLACEHOLDER = "\x00URL\x00"
_ABBREV_PLACEHOLDER = "\x00ABBR\x00"
_ABBREV_PAIR_PLACEHOLDER = "\x00ABBRP\x00"
_DECIMAL_PLACEHOLDER = "\x00DEC\x00"
_ELLIPSIS_PLACEHOLDER = "\x00ELL\x00"

_URL_RE = re.compile(r"https?://[^\s.!?,;:)]+(?:\.[^\s.!?,;:)]+)*")
_DECIMAL_RE = re.compile(r"(\d)\.(\d)")
_ELLIPSIS_RE = re.compile(r"\.\.\.")

# Build abbreviation regex: word boundary + abbreviation + period
_abbrev_alt = "|".join(
    re.escape(a) for a in sorted(_ABBREVIATIONS, key=len, reverse=True)
)
_ABBREV_RE = re.compile(rf"\b({_abbrev_alt})\.", re.IGNORECASE)

_abbrev_pair_alt = "|".join(
    re.escape(a) for a in sorted(_ABBREVIATION_PAIRS, key=len, reverse=True)
)
_ABBREV_PAIR_RE = re.compile(rf"\b({_abbrev_pair_alt})\.", re.IGNORECASE)

# Sentence boundary: punctuation followed by whitespace then uppercase or end-of-string
_SENTENCE_SPLIT_RE = re.compile(r"([.!?]+)(?:\s+(?=[A-Z])|$)")

# Markdown patterns (order matters — code blocks first)
_MD_CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
_MD_INLINE_CODE_RE = re.compile(r"`[^`]+`")
_MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\([^)]+\)")
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_MD_HEADER_RE = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_MD_BOLD_ITALIC_RE = re.compile(r"(\*{1,3}|_{1,3})")
_MD_HR_RE = re.compile(r"^[-*_]{3,}\s*$", re.MULTILINE)
_MD_EXTRA_BLANKS_RE = re.compile(r"\n{3,}")


def split_sentences(text: str) -> list[str]:
    """Split *text* into sentences using regex heuristics.

    Handles abbreviations (Mr., Dr., etc.), decimal numbers (3.14),
    URLs (http://...), and ellipsis (...) without incorrectly splitting.
    """
    if not text or not text.strip():
        return []

    working = text

    # 1. Protect URLs
    urls: list[str] = []

    def _save_url(m: re.Match) -> str:
        urls.append(m.group(0))
        return f"{_URL_PLACEHOLDER}{len(urls) - 1}{_URL_PLACEHOLDER}"

    working = _URL_RE.sub(_save_url, working)

    # 2. Protect two-part abbreviations (i.e., e.g.)
    abbrev_pairs: list[str] = []

    def _save_abbrev_pair(m: re.Match) -> str:
        abbrev_pairs.append(m.group(0))
        return f"{_ABBREV_PAIR_PLACEHOLDER}{len(abbrev_pairs) - 1}{_ABBREV_PAIR_PLACEHOLDER}"

    working = _ABBREV_PAIR_RE.sub(_save_abbrev_pair, working)

    # 3. Protect single-word abbreviations
    abbreviations: list[str] = []

    def _save_abbrev(m: re.Match) -> str:
        abbreviations.append(m.group(0))
        return f"{_ABBREV_PLACEHOLDER}{len(abbreviations) - 1}{_ABBREV_PLACEHOLDER}"

    working = _ABBREV_RE.sub(_save_abbrev, working)

    # 4. Protect decimals
    decimals: list[str] = []

    def _save_decimal(m: re.Match) -> str:
        decimals.append(m.group(0))
        return f"{m.group(1)}{_DECIMAL_PLACEHOLDER}{len(decimals) - 1}{_DECIMAL_PLACEHOLDER}{m.group(2)}"

    working = _DECIMAL_RE.sub(_save_decimal, working)

    # 5. Protect ellipsis
    ellipses: list[str] = []

    def _save_ellipsis(m: re.Match) -> str:
        ellipses.append(m.group(0))
        return f"{_ELLIPSIS_PLACEHOLDER}{len(ellipses) - 1}{_ELLIPSIS_PLACEHOLDER}"

    working = _ELLIPSIS_RE.sub(_save_ellipsis, working)

    # 6. Split on sentence boundaries
    parts = _SENTENCE_SPLIT_RE.split(working)

    # Recombine punctuation with preceding text: parts = [text, punct, text, punct, ...]
    sentences: list[str] = []
    i = 0
    while i < len(parts):
        segment = parts[i]
        if i + 1 < len(parts) and re.fullmatch(r"[.!?]+", parts[i + 1]):
            segment += parts[i + 1]
            i += 2
        else:
            i += 1
        sentences.append(segment)

    # 7. Restore placeholders
    def _restore(s: str) -> str:
        for idx, url in enumerate(urls):
            s = s.replace(f"{_URL_PLACEHOLDER}{idx}{_URL_PLACEHOLDER}", url)
        for idx, ap in enumerate(abbrev_pairs):
            s = s.replace(
                f"{_ABBREV_PAIR_PLACEHOLDER}{idx}{_ABBREV_PAIR_PLACEHOLDER}", ap
            )
        for idx, ab in enumerate(abbreviations):
            s = s.replace(f"{_ABBREV_PLACEHOLDER}{idx}{_ABBREV_PLACEHOLDER}", ab)
        for idx, dec in enumerate(decimals):
            s = s.replace(f"{_DECIMAL_PLACEHOLDER}{idx}{_DECIMAL_PLACEHOLDER}", ".")
        for idx, ell in enumerate(ellipses):
            s = s.replace(f"{_ELLIPSIS_PLACEHOLDER}{idx}{_ELLIPSIS_PLACEHOLDER}", ell)
        return s

    result = [_restore(s).strip() for s in sentences]
    return [s for s in result if s]


def strip_markdown(text: str) -> str:
    """Remove Markdown formatting, returning plain text."""
    if not text:
        return text

    result = text

    # Order matters: remove block-level constructs first
    result = _MD_CODE_BLOCK_RE.sub("", result)
    result = _MD_INLINE_CODE_RE.sub("", result)
    result = _MD_IMAGE_RE.sub(r"\1", result)
    result = _MD_LINK_RE.sub(r"\1", result)
    result = _MD_HEADER_RE.sub("", result)
    result = _MD_HR_RE.sub("", result)
    result = _MD_BOLD_ITALIC_RE.sub("", result)

    # Collapse excessive blank lines
    result = _MD_EXTRA_BLANKS_RE.sub("\n\n", result)

    return result.strip()


def detect_language(text: str) -> str:
    """Detect the language of *text* and return an ISO 639-1 code (e.g. ``"en"``)."""
    if not text or not text.strip():
        return "en"

    detected: Language | None = _detector.detect_language_of(text)
    if detected is None:
        return "en"

    return detected.iso_code_639_1.name.lower()


def preprocess(text: str) -> tuple[str, str]:
    """Run the full text preprocessing pipeline.

    Returns ``(cleaned_text, language_code)`` where *cleaned_text* has Markdown
    stripped and *language_code* is an ISO 639-1 two-letter code detected from
    the cleaned text.
    """
    cleaned = strip_markdown(text)
    language = detect_language(cleaned)
    return cleaned, language
