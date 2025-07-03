"""Entry point for running the FastAPI server on platforms like Replit."""

try:
    from api.app import app
except ModuleNotFoundError as exc:  # pragma: no cover - triggers only when deps missing
    if exc.name == "fastapi":
        raise SystemExit(
            "FastAPI is not installed. Run './setup.sh' to install required dependencies."
        ) from exc
    raise


if __name__ == "__main__":
    import uvicorn
    from api.config import settings

    uvicorn.run(app, host=settings.server_host, port=settings.server_port)
