"""Utilities for configuring application logging."""

from __future__ import annotations

import logging


def setup_logging(level: str) -> None:
    """Configure Python logging.

    Parameters
    ----------
    level:
        Logging verbosity name such as ``"INFO"`` or ``"DEBUG"``.
    """
    numeric = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=True,
    )
