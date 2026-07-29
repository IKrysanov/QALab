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
    level = config.getoption("log_level") or "INFO"
    configure_logging(level=level)


@pytest.fixture(scope="session")
def api_base_url(request) -> str:
    """Получить API URL только для тестов, которым он действительно нужен."""

    return (
        request.config.getoption("base_url")
        or config_env.get("API_BASE_URL", required=True)
        or ""
    )


@pytest.fixture(scope="session")
def api_config(api_base_url) -> APIConfig:

    return APIConfig(
        host=api_base_url,
        default_headers={"cookie": "test-cookies"},
    )


@pytest.fixture(scope="session")
def web_ui_config(api_base_url) -> WebUIConfig:

    return WebUIConfig(host=api_base_url)


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


@pytest.fixture(scope="session")
def openshift_config():
    """Собрать OpenShiftConfig из общего ConfigEnv."""

    from src.openshift import OpenShiftConfig

    namespace = config_env.get("OPENSHIFT_NAMESPACE", required=True)
    verify_ssl = (
        config_env.get_bool("OPENSHIFT_VERIFY_SSL")
        if _optional_env("OPENSHIFT_VERIFY_SSL") is not None
        else None
    )
    connect_timeout = config_env.get_float(
        "OPENSHIFT_CONNECT_TIMEOUT",
        default=5.0,
    )
    read_timeout = config_env.get_float(
        "OPENSHIFT_READ_TIMEOUT",
        default=30.0,
    )
    wait_timeout = config_env.get_float(
        "OPENSHIFT_WAIT_TIMEOUT",
        default=300.0,
    )
    poll_interval = config_env.get_float(
        "OPENSHIFT_POLL_INTERVAL",
        default=2.0,
    )
    log_limit_bytes = config_env.get_int(
        "OPENSHIFT_LOG_LIMIT_BYTES",
        default=1_000_000,
    )
    exec_timeout = config_env.get_float(
        "OPENSHIFT_EXEC_TIMEOUT",
        default=60.0,
    )
    exec_output_limit_bytes = config_env.get_int(
        "OPENSHIFT_EXEC_OUTPUT_LIMIT_BYTES",
        default=1_000_000,
    )

    return OpenShiftConfig(
        namespace=namespace or "",
        auth_mode=_optional_env("OPENSHIFT_AUTH_MODE") or "auto",
        kubeconfig_path=_optional_env("OPENSHIFT_KUBECONFIG"),
        context=_optional_env("OPENSHIFT_CONTEXT"),
        verify_ssl=verify_ssl,
        ssl_ca_cert=_optional_env("OPENSHIFT_CA_CERT"),
        connect_timeout=(
            connect_timeout if connect_timeout is not None else 5.0
        ),
        read_timeout=read_timeout if read_timeout is not None else 30.0,
        wait_timeout=wait_timeout if wait_timeout is not None else 300.0,
        poll_interval=(
            poll_interval if poll_interval is not None else 2.0
        ),
        log_limit_bytes=(
            log_limit_bytes
            if log_limit_bytes is not None
            else 1_000_000
        ),
        exec_timeout=(
            exec_timeout if exec_timeout is not None else 60.0
        ),
        exec_output_limit_bytes=(
            exec_output_limit_bytes
            if exec_output_limit_bytes is not None
            else 1_000_000
        ),
    )


@pytest.fixture(scope="session")
@allure.title("Create OpenShift client")
def openshift_client(openshift_config):
    """Session-scoped OpenShift-клиент для тестовых сценариев."""

    from src.openshift import OpenShiftClient

    with OpenShiftClient(openshift_config) as client:
        yield client


@pytest.fixture(scope="session")
@allure.title("Airflow webserver container")
def web_server(openshift_client):
    """Актуальный webserver pod; имя заново разрешается перед операцией."""

    return openshift_client.container(
        "airflow-webserver-*",
        container_name="webserver",
    )
