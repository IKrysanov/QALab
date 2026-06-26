"""Эндпоинты мониторинга Airflow Stable REST API v1 (Airflow 2.x): health, version.

Базовый префикс ``/api/v1`` задаётся через ``APIConfig.prefix_path``.
В отличие от v2 (``/monitor/health``), в v1 ручки лежат прямо в корне API:
``/api/v1/health`` и ``/api/v1/version``.
"""

from http import HTTPStatus
from typing import Any

from httpx import Response

from ..base import BaseEndpoint
from ...http_client import StatusCode
from ...models.v1.monitor import HealthInfoResponse, VersionInfo


class MonitorEndpoint(BaseEndpoint):
    """Операции с /api/v1/health и /api/v1/version."""

    async def health(
            self,
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """GET /api/v1/health — состояние компонентов Airflow."""
        return await self._http.get(
            "/health",
            expected_status=expected_status,
            response_model=HealthInfoResponse if expected_status == HTTPStatus.OK else None,
            **kwargs,
        )

    async def version(
            self,
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """GET /api/v1/version — версия Airflow."""
        return await self._http.get(
            "/version",
            expected_status=expected_status,
            response_model=VersionInfo if expected_status == HTTPStatus.OK else None,
            **kwargs,
        )
