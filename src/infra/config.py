"""Конфиги внешних систем для health-check клиента."""

from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass(frozen=True)
class HTTPSystemConfig:
    """Базовый конфиг HTTP-системы, проверяемой через curl.

    :param base_url: базовый URL, например ``http://trino:8080``
    :param name: логическое имя системы (для логов и результата)
    :param health_path: путь health-эндпоинта, добавляется к ``base_url``
    :param username: имя пользователя для basic-auth (опционально)
    :param password: пароль для basic-auth (опционально)
    :param headers: дополнительные HTTP-заголовки
    :param timeout: таймаут запроса в секундах (curl --max-time)
    :param verify_tls: проверять ли TLS-сертификат (False -> curl --insecure)
    :param expected_status: набор допустимых HTTP-кодов; пусто -> любой 2xx/3xx
    """

    base_url: str
    name: str = "http-system"
    health_path: str = "/"
    username: str = ""
    password: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    timeout: float = 10.0
    verify_tls: bool = True
    expected_status: Tuple[int, ...] = ()

    @property
    def url(self) -> str:
        """Полный URL health-эндпоинта."""
        return f"{self.base_url.rstrip('/')}/{self.health_path.lstrip('/')}"


@dataclass(frozen=True)
class TrinoConfig(HTTPSystemConfig):
    """Trino: health-эндпоинт ``/v1/info`` (отдаёт 200 на живом координаторе)."""

    name: str = "trino"
    health_path: str = "/v1/info"


@dataclass(frozen=True)
class ClickHouseConfig(HTTPSystemConfig):
    """ClickHouse: health-эндпоинт ``/ping`` (отдаёт ``Ok.\\n`` и 200)."""

    name: str = "clickhouse"
    health_path: str = "/ping"


@dataclass(frozen=True)
class SparkConfig(HTTPSystemConfig):
    """Spark: REST History Server ``/api/v1/applications`` (или UI мастера ``/``)."""

    name: str = "spark"
    health_path: str = "/api/v1/applications"


@dataclass(frozen=True)
class GreenPlumConfig:
    """GreenPlum (PostgreSQL wire protocol), проверяется через psql.

    :param host: хост координатора
    :param port: порт (по умолчанию 5432)
    :param database: имя БД
    :param username: пользователь
    :param password: пароль (передаётся через PGPASSWORD, не в argv)
    :param name: логическое имя системы
    :param timeout: таймаут подключения в секундах (PGCONNECT_TIMEOUT)
    :param query: проверочный запрос
    """

    host: str
    port: int = 5432
    database: str = "postgres"
    username: str = "gpadmin"
    password: str = ""
    name: str = "greenplum"
    timeout: float = 10.0
    query: str = "SELECT 1"
