import os
from abc import ABC, abstractmethod
import httpx
from dotenv import load_dotenv
from src.models import RawSignal

load_dotenv()


def _get_proxy() -> str | None:
    """Auto-detect proxy from .env, env vars, or common local ports."""
    # Explicit .env config takes priority
    explicit = os.getenv("PROXY")
    if explicit:
        return explicit

    for var in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"):
        val = os.environ.get(var, "")
        if val:
            return val

    # Check common local proxy ports
    import socket
    for port in (7890, 7891, 1080, 10808, 10809, 8118):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.3)
            s.connect(("127.0.0.1", port))
            s.close()
            return f"http://127.0.0.1:{port}"
        except (OSError, ConnectionRefusedError):
            continue
    return None


class BaseCollector(ABC):
    """Abstract collector. Each source implements collect()."""

    def __init__(self, name: str, display_name: str, config: dict | None = None):
        self.name = name
        self.display_name = display_name
        self.config = config or {}

        proxy = _get_proxy()
        client_kwargs = {
            "timeout": 30,
            "headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                )
            },
            "follow_redirects": True,
        }
        if proxy:
            client_kwargs["proxy"] = proxy

        self.client = httpx.Client(**client_kwargs)

    @abstractmethod
    def collect(self) -> list[RawSignal]:
        ...

    def close(self):
        self.client.close()
