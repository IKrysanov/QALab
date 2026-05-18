"""
Конфигурация API-клиента.

Содержит неизменяемый dataclass `APIConfig`, который хранит параметры
подключения к API (хост, протокол, путь-префикс, порт, таймаут и др.)
и предоставляет вычисляемое свойство `base_url` для удобного получения
полного базового URL, используемого http-клиентом.
"""

from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass(frozen=True)
class APIConfig:
    """
    Настройки подключения к API.

    Параметры:
    - host: доменное имя или хост с портом (без схемы), например "api.example.com".
    - protocol: схема: "http" или "https" (по умолчанию "https").
    - prefix_path: префикс пути, добавляемый к базовому URL, например "/api/v1" или "api/v1".
                   Если пустая строка — префикс не добавляется.
    - port: опциональный номер порта. Если указан, включается в `base_url` как `host:port`.
    - timeout: таймаут в секундах для запросов.
    - verify_ssl: проверять ли SSL-сертификат при HTTPS.
    - follow_redirects: следовать ли редиректам (по умолчанию True).
    - default_headers: словарь заголовков по умолчанию.
    - max_connections, max_keepalive_connections: настройки пула соединений.
    """

    host: str
    protocol: Literal["http", "https"] = "https"
    prefix_path: str = ""
    port: Optional[int] = None
    timeout: float = 10.0
    verify_ssl: bool = True
    follow_redirects: bool = True
    default_headers: dict = field(default_factory=dict)
    max_connections: int = 100
    max_keepalive_connections: int = 20

    @property
    def base_url(self) -> str:
        """
        Собирает и возвращает базовый URL в формате "{protocol}://{host[:port]}{/prefix}".

        Правила формирования:
        - Если указан `port`, он добавляется к `host` через двоеточие: "host:port".
        - `prefix_path` нормализуется: обрезаются внешние слеши, затем,
          если префикс непустой, добавляется один ведущий слеш.
            Примеры:
              prefix_path = ""       -> '' (нет суффикса)
              prefix_path = "api/v1" -> '/api/v1'
              prefix_path = "/api"   -> '/api'
        - В результирующем `base_url` не должно быть конечного слеша,
          кроме случаев, когда `prefix_path` явно задаёт такой фрагмент.
        - Возвращаемое значение пригодно для использования как `httpx.AsyncClient(base_url=...)`.

        Примеры:
          APIConfig(host="api.example.com") -> "https://api.example.com"
          APIConfig(host="api.example.com", port=8080) -> "https://api.example.com:8080"
          APIConfig(host="api.example.com", prefix_path="/api/v1") -> "https://api.example.com/api/v1"
        """

        netloc = f"{self.host}:{self.port}" if self.port else self.host
        prefix = self.prefix_path.strip("/")
        suffix = f"/{prefix}" if prefix else ""
        return f"{self.protocol}://{netloc}{suffix}"
