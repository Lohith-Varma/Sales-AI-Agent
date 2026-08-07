"""Start the development ASGI server using validated environment settings."""

import uvicorn
from ai.config.settings import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "ai.main:create_app",
        factory=True,
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
        log_config=None,
    )


if __name__ == "__main__":
    main()
