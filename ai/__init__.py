"""Pay-in-3 AI Voice Sales Co-Pilot application package.

The package is intentionally organized around small agent and infrastructure
boundaries. Public package metadata is kept here; application construction lives
in :mod:`ai.main` to avoid import-time side effects.
"""

from importlib.metadata import PackageNotFoundError, version
from typing import Final

_DISTRIBUTION_NAME: Final = "pay-in-3-sales-copilot"
_SOURCE_VERSION: Final = "0.1.0"


def _resolve_version() -> str:
    """Return installed package metadata with a source-tree fallback.

    Editable and wheel installations expose distribution metadata through
    ``importlib.metadata``. The fallback keeps diagnostics usable when the package
    is imported directly from a source checkout before installation.
    """

    try:
        return version(_DISTRIBUTION_NAME)
    except PackageNotFoundError:
        return _SOURCE_VERSION


__version__: Final = _resolve_version()

__all__ = ["__version__"]
