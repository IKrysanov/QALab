"""Конфигурации HTTP-клиентов."""

from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass(frozen=True)
class BaseHTTPConfig:
    """
    Общая база для любых HTTP-клиентов поверх httpx.
    Прямо использовать обычно не нужно — лучше APIConfig или WebUIConfig.
    """

    host: str
    protocol: Literal["http", "https"] = "https"
    port: Optional[int] = None
    prefix_path: str = ""
    timeout: float = 10.0
    verify_ssl: bool = True
    follow_redirects: bool = True
    default_headers: dict[str, str] = field(default_factory=dict)
    max_connections: int = 100
    max_keepalive_connections: int = 20
    request_trace_id_header: str = "X-TRACE-ID"
    max_log_body: int = 4096

    def __post_init__(self):
        if self.host.startswith(("http://", "https://")):
            raise ValueError(
                f"host should not include protocol, got {self.host!r}. "
                f"Use protocol parameter instead."
            )

        if "//" in self.prefix_path.strip("/"):
            raise ValueError(f"prefix_path contains double slashes: {self.prefix_path!r}")

    @property
    def root_url(self) -> str:
        netloc = f"{self.host}:{self.port}" if self.port else self.host
        return f"{self.protocol}://{netloc}"

    @property
    def base_url(self) -> str:
        prefix = self.prefix_path.strip("/")
        suffix = f"/{prefix}" if prefix else ""
        return f"{self.root_url}{suffix}"


@dataclass(frozen=True)
class APIConfig(BaseHTTPConfig):
    """Конфиг для REST API. По умолчанию Accept: application/json."""

    default_headers: dict = field(
        default_factory=lambda: {"Accept": "application/json"}
    )


@dataclass(frozen=True)
class WebUIConfig(BaseHTTPConfig):
    """
    Конфиг для тестов веб-приложения через httpx.

    Отличается от APIConfig:
      - timeout 30 сек вместо 10 (страницы тяжелее JSON);
      - дефолтные заголовки имитируют браузер;
      - prefix_path пуст (UI обычно на корне).
    """

    timeout: float = 30.0
    user_agent: str = "Mozilla/5.0 (compatible; QALab/1.0; +tests)"
    default_headers: dict[str, str] = field(
        default_factory=lambda: {
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }
    )

    @property
    def all_headers(self) -> dict[str, str]:
        """Итоговые заголовки — default_headers + User-Agent."""
        return {**self.default_headers, "User-Agent": self.user_agent}
