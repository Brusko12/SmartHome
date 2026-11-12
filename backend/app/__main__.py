import argparse

import uvicorn

from app.core.config import Settings


def main() -> None:
    parser = argparse.ArgumentParser(description="SmartHome development server")
    parser.add_argument("--reload", action="store_true", help="Reload when backend files change")
    args = parser.parse_args()
    settings = Settings()
    uvicorn.run(
        "app.main:create_app",
        factory=True,
        host="127.0.0.1",
        port=settings.port,
        log_level=settings.log_level,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
