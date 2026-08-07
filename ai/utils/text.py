"""Deterministic text normalization, bounding, and hashing helpers."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Iterable
from typing import Final

_INLINE_WHITESPACE: Final = re.compile(r"[^\S\r\n]+")
_MULTIPLE_BLANK_LINES: Final = re.compile(r"\n{3,}")
_ALL_WHITESPACE: Final = re.compile(r"\s+")
_SAFE_IDENTIFIER_CHARACTER: Final = re.compile(r"[^A-Za-z0-9._-]+")
_SENTENCE_BOUNDARY: Final = re.compile(r"(?<=[.!?])\s+")


def _remove_control_characters(value: str, *, preserve_newlines: bool) -> str:
    """Remove invisible control characters while optionally retaining line breaks."""

    permitted = {"\n", "\t"} if preserve_newlines else set()
    return "".join(
        character
        for character in value
        if character in permitted or unicodedata.category(character) != "Cc"
    )


def normalize_utterance(value: str) -> str:
    """Normalize short conversation text to one clean line."""

    normalized = unicodedata.normalize("NFKC", value)
    normalized = _remove_control_characters(normalized, preserve_newlines=False)
    return _ALL_WHITESPACE.sub(" ", normalized).strip()


def normalize_document_text(value: str) -> str:
    """Normalize document text while retaining paragraph boundaries."""

    normalized = unicodedata.normalize("NFKC", value).replace("\r\n", "\n").replace("\r", "\n")
    normalized = _remove_control_characters(normalized, preserve_newlines=True)
    normalized = _INLINE_WHITESPACE.sub(" ", normalized)
    lines = (line.strip() for line in normalized.splitlines())
    normalized = "\n".join(lines)
    return _MULTIPLE_BLANK_LINES.sub("\n\n", normalized).strip()


def truncate_text(value: str, max_characters: int, *, suffix: str = "…") -> str:
    """Bound text without splitting a word when a boundary is available."""

    if max_characters <= 0:
        raise ValueError("max_characters must be positive")
    if len(suffix) >= max_characters:
        raise ValueError("suffix must be shorter than max_characters")
    if len(value) <= max_characters:
        return value

    available = max_characters - len(suffix)
    candidate = value[:available]
    boundary = max(candidate.rfind(" "), candidate.rfind("\n"))
    if boundary >= max(1, available // 2):
        candidate = candidate[:boundary]
    return candidate.rstrip() + suffix


def join_bounded_text(
    items: Iterable[str],
    *,
    max_characters: int,
    separator: str = "\n",
) -> str:
    """Join items in order without exceeding a hard character budget."""

    if max_characters <= 0:
        raise ValueError("max_characters must be positive")

    result: list[str] = []
    used = 0
    for item in items:
        normalized = item.strip()
        if not normalized:
            continue
        separator_size = len(separator) if result else 0
        remaining = max_characters - used - separator_size
        if remaining <= 0:
            break
        if len(normalized) > remaining:
            if remaining > 1:
                result.append(truncate_text(normalized, remaining, suffix="…"))
            break
        result.append(normalized)
        used += separator_size + len(normalized)
    return separator.join(result)


def split_sentences(value: str) -> tuple[str, ...]:
    """Return a lightweight sentence split suitable for guardrail claim checks."""

    normalized = normalize_utterance(value)
    if not normalized:
        return ()
    return tuple(part.strip() for part in _SENTENCE_BOUNDARY.split(normalized) if part.strip())


def sha256_text(value: str) -> str:
    """Return a stable lowercase SHA-256 digest for UTF-8 text."""

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def stable_chunk_id(document_id: str, chunk_index: int, chunk_text: str) -> str:
    """Create a deterministic Chroma-safe identifier for one document chunk."""

    if chunk_index < 0:
        raise ValueError("chunk_index cannot be negative")
    safe_document_id = _SAFE_IDENTIFIER_CHARACTER.sub("_", document_id).strip("._-")
    if not safe_document_id:
        raise ValueError("document_id must contain at least one safe identifier character")
    digest_prefix = sha256_text(chunk_text)[:12]
    return f"{safe_document_id}:{chunk_index}:{digest_prefix}"


__all__ = [
    "join_bounded_text",
    "normalize_document_text",
    "normalize_utterance",
    "sha256_text",
    "split_sentences",
    "stable_chunk_id",
    "truncate_text",
]
