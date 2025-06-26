"""Entry point for running the FastAPI server on platforms like Replit."""

try:
    from api.app import app
except ModuleNotFoundError as exc:  # pragma: no cover - triggers only when deps missing
    if exc.name == "fastapi":
        raise SystemExit(
            "FastAPI is not installed. Run './setup.sh' to install all dependencies."
        ) from exc
    raise


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
