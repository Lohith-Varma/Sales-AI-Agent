"""Pydantic contracts shared across agents, orchestration, and API boundaries.

Schema modules are intentionally not re-exported from this package initializer.
Importing models from their defining modules makes dependencies explicit and
prevents circular imports as the orchestration state composes agent outputs.

The schema dependency order is:

``enums`` -> ``common`` -> agent-specific schemas -> ``orchestration`` ->
transport request and response schemas.
"""

__all__: tuple[str, ...] = ()
