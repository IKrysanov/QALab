"""Эндпоинты для системных ресурсов Airflow API v2.

Покрывает теги: Monitor (health), Version, Config, Login.
"""

from http import HTTPStatus
from typing import Optional

from httpx import Response

from ..endpoints.base import BaseEndpoint
from ..http_client import StatusCode
from ..models.monitor import Config, HealthInfoResponse, VersionInfo


class MonitorEndpoint(BaseEndpoint):

    async def health(
            self,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/monitor/health — состояние компонентов Airflow."""
        return await self._http.get(
            "/monitor/health",
            expected_status=expected_status,
            response_model=HealthInfoResponse if expected_status == HTTPStatus.OK else None,
        )

    async def version(
            self,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/version — версия Airflow."""
        return await self._http.get(
            f"{BASE}/version",
            expected_status=expected_status,
            response_model=VersionInfo if expected_status == HTTPStatus.OK else None,
        )

    async def get_config(
            self,
            section: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/config — конфигурация Airflow (требует admin прав)."""
        params = {"section": section} if section else None
        return await self._http.get(
            f"{BASE}/config",
            params=params,
            expected_status=expected_status,
            response_model=Config if expected_status == HTTPStatus.OK else None,
        )

    async def get_config_value(
            self,
            section: str,
            option: str,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/config/section/{section}/option/{option}."""
        return await self._http.get(
            f"{BASE}/config/section/{section}/option/{option}",
            expected_status=expected_status,
        )

    async def login(
            self,
            next_url: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/auth/login."""
        params = {"next": next_url} if next_url else None
        return await self._http.get(
            f"{BASE}/auth/login",
            params=params,
            expected_status=expected_status,
        )

    async def logout(
            self,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/auth/logout."""
        return await self._http.get(
            f"{BASE}/auth/logout",
            expected_status=expected_status,
        )
