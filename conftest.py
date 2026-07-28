from typing import Optional

import allure
import httpx
import pytest
import pytest_asyncio

from src.async_api_client.config import APIConfig, WebUIConfig
from src.async_api_client.auth import SessionLoginAuth
from src.async_api_client.client import AsyncAPIClient
from src.infra import DataSystemHealthClient

from utils.logger import configure_logging
from utils.environment import ConfigEnv

config_env = ConfigEnv()


def _optional_env(name: str) -> Optional[str]:
    value = config_env.get(name)
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def pytest_addoption(parser):
    parser.addoption(
        "--base_url",
        action="store",
        default=None,
        help="Base API URL (overrides API_BASE_URL from environment)",
    )


def pytest_configure(config):
    base_url = config.getoption("base_url") or config_env.get("API_BASE_URL", required=True)
    config.base_url = base_url

    level = config.getoption("log_level") or "INFO"
    configure_logging(level=level)


@pytest.fixture(scope="session")
def api_config(request) -> APIConfig:
    base_url = request.config.base_url

    return APIConfig(host=base_url, default_headers={"cookie": "test-cookies"})


@pytest.fixture(scope="session")
def web_ui_config(request) -> WebUIConfig:
    base_url = request.config.base_url

    return WebUIConfig(host=base_url)


@pytest_asyncio.fixture(loop_scope="session", scope="session")
@allure.title("Create HTTP session for API client")
async def http_session(api_config):
    async with httpx.AsyncClient(
            base_url=api_config.base_url,
            timeout=api_config.timeout,
            verify=api_config.verify_ssl,
            follow_redirects=api_config.follow_redirects,
            headers=api_config.default_headers,
    ) as session:
        yield session


@pytest_asyncio.fixture
async def api_client(api_config, http_session):
    async with AsyncAPIClient(
            api_config, session=http_session, validate_request=False, validate_response=False,
    ) as client:
        yield client


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def session_auth(http_session) -> SessionLoginAuth:
    return SessionLoginAuth(
        username="admin",
        password="admin",
        login_url="/login/",
        session=http_session,
    )


@pytest_asyncio.fixture
async def api_client_with_auth_session(api_config, http_session, session_auth):
    async with AsyncAPIClient(
            api_config,
            auth=session_auth,
            session=http_session,
    ) as client:
        yield client


@pytest.fixture(scope="session")
@allure.title("Health-check client for external data systems")
def health_client() -> DataSystemHealthClient:
    """Клиент health-check'ов внешних систем (GreenPlum/Trino/ClickHouse/Spark).

    Если задана ``KRB_PRINCIPAL``, в setup делается ``kinit`` (пароль —
    ``KRB_PASSWORD``), чтобы curl с ``kerberos=True`` ходил по валидному тикету.
    """
    client = DataSystemHealthClient()

    principal = config_env.get("KRB_PRINCIPAL")
    if principal:
        password = config_env.get("KRB_PASSWORD", required=True)
        client.kinit(principal, password)

    return client


@pytest.fixture(scope="session")
def s3_config():
    """Собрать явный S3Config из общего ConfigEnv."""

    from src.s3 import S3Config

    bucket_name = config_env.get("S3_BUCKET_NAME", required=True)
    verify_ssl = (
        config_env.get_bool("S3_VERIFY_SSL")
        if _optional_env("S3_VERIFY_SSL") is not None
        else None
    )
    connect_timeout = config_env.get_float(
        "S3_CONNECT_TIMEOUT",
        default=5.0,
    )
    read_timeout = config_env.get_float(
        "S3_READ_TIMEOUT",
        default=30.0,
    )
    max_attempts = config_env.get_int(
        "S3_MAX_ATTEMPTS",
        default=3,
    )

    return S3Config(
        bucket_name=bucket_name or "",
        endpoint_url=_optional_env("S3_ENDPOINT_URL"),
        region_name=(
            _optional_env("AWS_REGION")
            or _optional_env("AWS_DEFAULT_REGION")
        ),
        aws_access_key_id=_optional_env("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=_optional_env("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=_optional_env("AWS_SESSION_TOKEN"),
        profile_name=_optional_env("AWS_PROFILE"),
        verify_ssl=verify_ssl,
        addressing_style=_optional_env("S3_ADDRESSING_STYLE") or "auto",
        connect_timeout=(
            connect_timeout if connect_timeout is not None else 5.0
        ),
        read_timeout=read_timeout if read_timeout is not None else 30.0,
        max_attempts=max_attempts if max_attempts is not None else 3,
    )


@pytest.fixture
@allure.title("Create S3 client")
def s3_client(s3_config):
    """Изолированный S3-клиент с гарантированным закрытием после теста."""

    # Локальный импорт не запускает настройку S3-логгера раньше pytest_configure.
    from src.s3 import S3Client

    with S3Client(s3_config) as client:
        yield client
