"""Utility helpers for the API server."""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse
from html.parser import HTMLParser

__all__ = ["is_public_url", "html_to_text"]


def is_public_url(url: str) -> bool:
    """Return True if ``url`` points to a public host."""
    host = urlparse(url).hostname
    if not host:
        return False
    if host.lower() == "localhost":
        return False
    try:
        ip = ipaddress.ip_address(host)
        return not (
            ip.is_private
            or ip.is_loopback
            or ip.is_reserved
            or ip.is_link_local
            or ip.is_multicast
        )
    except ValueError:
        # Host isn't an IP address; assume it's valid
        return True


class _TextExtractor(HTMLParser):
    """Internal HTML parser that collects text while skipping script/style tags."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip: bool = False

    def handle_starttag(self, tag: str, _attrs) -> None:  # pragma: no cover - trivial
        if tag in {"script", "style"}:
            self._skip = True

    def handle_endtag(self, tag: str) -> None:  # pragma: no cover - trivial
        if tag in {"script", "style"}:
            self._skip = False

    def handle_data(self, data: str) -> None:  # pragma: no cover - trivial
        if not self._skip:
            self.parts.append(data)

    def text(self) -> str:
        return " ".join(" ".join(self.parts).split())


def html_to_text(html: str) -> str:
    """Return ``html`` with tags stripped and whitespace normalized."""
    parser = _TextExtractor()
    parser.feed(html)
    return parser.text()

