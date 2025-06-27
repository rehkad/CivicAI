"""Entry point for running the FastAPI server on platforms like Replit."""

try:
    from api.app import app
except ModuleNotFoundError as exc:  # pragma: no cover - triggers only when deps missing
    if exc.name == "fastapi":
        import subprocess
        from pathlib import Path

        script = Path(__file__).with_name("setup.sh")
        if script.exists():
            try:
                subprocess.run(["bash", str(script)], check=True)
                from api.app import app  # retry after installing deps
            except Exception:
                raise SystemExit(
                    "FastAPI is not installed. Run './setup.sh' to install all dependencies."
                ) from exc
        else:
            raise SystemExit(
                "FastAPI is not installed. Run './setup.sh' to install all dependencies."
            ) from exc
    else:
        raise


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000)
