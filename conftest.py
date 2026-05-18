import httpx
import pytest
import pytest_asyncio

from src.async_api_client.config import APIConfig
from src.async_api_client.auth import SessionLoginAuth
from src.async_api_client.client import AsyncAPIClient

from utils.logger import configure_logging
from utils.environment import ConfigEnv

config_env = ConfigEnv()


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

    return APIConfig(
        host=base_url,
        protocol="https",
        timeout=10.0,
        default_headers={"Accept": "application/json"},
    )


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def http_session(api_config):
    async with httpx.AsyncClient(
            base_url=api_config.base_url,
            timeout=api_config.timeout,
            verify=api_config.verify_ssl,
            follow_redirects=api_config.follow_redirects,
    ) as session:
        yield session


@pytest_asyncio.fixture
async def api_client(api_config, http_session):
    async with AsyncAPIClient(api_config, session=http_session) as client:
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
