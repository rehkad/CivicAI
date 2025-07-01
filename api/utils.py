import ipaddress
from urllib.parse import urlparse


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
