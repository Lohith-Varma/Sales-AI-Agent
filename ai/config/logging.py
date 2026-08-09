"""Structured logging configuration with defensive PII redaction."""

from __future__ import annotations

import logging
import logging.config
import sys
from collections.abc import Mapping, MutableMapping
from typing import Any, Final, cast

import structlog

from ai.config.settings import LogFormat, Settings

_REDACTED: Final = "[REDACTED]"

# Matching is deliberately broad. Application code should log identifiers and
# metrics rather than customer content; this processor is a second line of defense.
_SENSITIVE_KEY_PARTS: Final[tuple[str, ...]] = (
    "api_key",
    "authorization",
    "customer_name",
    "email",
    "entity",
    "mobile",
    "password",
    "phone",
    "raw_audio",
    "salary",
    "secret",
    "token",
    "transcript",
)


def _is_sensitive_key(key: object) -> bool:
    """Return whether a mapping key may identify or describe a customer."""

    normalized = str(key).casefold()
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def _redact_nested(value: object) -> object:
    """Recursively redact sensitive mapping values while preserving log shape."""

    if isinstance(value, Mapping):
        return {
            str(key): _REDACTED if _is_sensitive_key(key) else _redact_nested(item)
            for key, item in value.items()
        }
    if isinstance(value, tuple):
        return tuple(_redact_nested(item) for item in value)
    if isinstance(value, list):
        return [_redact_nested(item) for item in value]
    return value


def redact_sensitive_values(
    _logger: logging.Logger,
    _method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """Structlog processor that removes sensitive values from an event."""

    redacted = _redact_nested(event_dict)
    if not isinstance(redacted, MutableMapping):  # pragma: no cover - defensive
        return event_dict
    return redacted


def _shared_processors(redact_values: bool) -> list[Any]:
    """Build processors shared by structlog and standard-library loggers."""

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
        structlog.processors.StackInfoRenderer(),
    ]
    if redact_values:
        processors.append(redact_sensitive_values)
    processors.append(structlog.processors.format_exc_info)
    return processors


def configure_logging(settings: Settings) -> None:
    """Configure standard-library logging and structlog for the process.

    The function is safe to call more than once. Existing root handlers are
    replaced so development reloads and test application factories do not emit
    duplicate records.
    """

    shared_processors = _shared_processors(settings.log_redact_sensitive_values)
    renderer: Any
    if settings.log_format is LogFormat.JSON:
        renderer = structlog.processors.JSONRenderer(sort_keys=True)
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    # Keep the active stderr object owned by the host/test runner. Wrapping
    # ``sys.stderr.buffer`` in a new TextIOWrapper closes the shared stream when
    # logging is reconfigured, which breaks subsequent application factories.
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)


    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level)

    # These libraries can be verbose at INFO and may expose request metadata.
    for logger_name in ("httpcore", "httpx", "multipart", "urllib3"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    logging.captureWarnings(True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelNamesMapping()[settings.log_level]
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a structured logger, optionally bound to a component name."""

    logger = structlog.get_logger(name)
    bound = logger if name is None else logger.bind(component=name)
    return cast(structlog.stdlib.BoundLogger, bound)


__all__ = ["configure_logging", "get_logger", "redact_sensitive_values"]
