"""Strict JSON serialization and structured-model-output validation."""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Final, TypeVar
from uuid import UUID

from pydantic import BaseModel, SecretStr, ValidationError

_DEFAULT_MAX_JSON_CHARACTERS: Final = 100_000


class StructuredJSONError(ValueError):
    """Raised when model output is not one strict, schema-valid JSON object."""


def _reject_duplicate_keys(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    """Build a JSON object while rejecting ambiguous duplicate keys."""

    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StructuredJSONError(f"JSON object contains duplicate key: {key}")
        result[key] = value
    return result


def _reject_non_finite_number(value: str) -> None:
    """Reject NaN and infinity, which are not part of the JSON specification."""

    raise StructuredJSONError(f"JSON contains a non-finite number: {value}")


def load_json_object(
    raw_json: str,
    *,
    max_characters: int = _DEFAULT_MAX_JSON_CHARACTERS,
) -> dict[str, Any]:
    """Parse exactly one strict JSON object from untrusted model output.

    Markdown fences and explanatory prefixes/suffixes are intentionally rejected.
    Guardrails can therefore distinguish valid structured output from text that
    merely contains a JSON-looking fragment.
    """

    if not raw_json or not raw_json.strip():
        raise StructuredJSONError("model output is empty")
    if len(raw_json) > max_characters:
        raise StructuredJSONError("model output exceeds the configured JSON size limit")

    try:
        value = json.loads(
            raw_json,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite_number,
        )
    except StructuredJSONError:
        raise
    except json.JSONDecodeError as exc:
        # Do not include the source line because model output may contain PII.
        raise StructuredJSONError(
            f"model output is not valid JSON at line {exc.lineno}, column {exc.colno}"
        ) from exc

    if not isinstance(value, dict):
        raise StructuredJSONError("model output must be a JSON object")
    return value


ModelT = TypeVar("ModelT", bound=BaseModel)


def validate_json_model(
    raw_json: str,
    model_type: type[ModelT],
    *,
    max_characters: int = _DEFAULT_MAX_JSON_CHARACTERS,
) -> ModelT:
    """Parse strict JSON and validate it against a Pydantic model type."""

    parsed = load_json_object(raw_json, max_characters=max_characters)
    try:
        return model_type.model_validate(parsed)
    except ValidationError as exc:
        error_locations = tuple(
            ".".join(str(part) for part in error["loc"]) for error in exc.errors()
        )
        locations = ", ".join(error_locations[:10]) or "root"
        raise StructuredJSONError(f"model output failed schema validation at: {locations}") from exc


def _json_default(value: object) -> object:
    """Serialize application value types without exposing secret contents."""

    if isinstance(value, SecretStr):
        return "[REDACTED]"
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, UUID | Path | Enum):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, set | frozenset | tuple):
        return list(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def dump_json(value: object, *, pretty: bool = False) -> str:
    """Serialize a value deterministically for API or diagnostic use."""

    return json.dumps(
        value,
        default=_json_default,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
    )


__all__ = ["StructuredJSONError", "dump_json", "load_json_object", "validate_json_model"]
