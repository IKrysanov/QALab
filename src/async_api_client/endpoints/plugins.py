"""Эндпоинты для Plugin и Provider ресурсов Airflow API v2."""

from http import HTTPStatus
from typing import Optional

from httpx import Response

from ..endpoints.base import BaseEndpoint
from ..http_client import StatusCode
from ..models.monitor import (
    PluginCollectionResponse,
    PluginImportErrorCollectionResponse,
    ProviderCollectionResponse,
)


class PluginsEndpoint(BaseEndpoint):
    PATH = "/plugins"

    async def list(
            self,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/plugins."""
        params = {k: v for k, v in {
            "limit": limit,
            "offset": offset,
        }.items() if v is not None}
        return await self._http.get(
            self.PATH,
            params=params or None,
            expected_status=expected_status,
            response_model=PluginCollectionResponse if expected_status == HTTPStatus.OK else None,
        )

    async def get_import_errors(
            self,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/plugins/importErrors."""
        return await self._http.get(
            f"{self.PATH}/importErrors",
            expected_status=expected_status,
            response_model=PluginImportErrorCollectionResponse if expected_status == HTTPStatus.OK else None,
        )


class ProvidersEndpoint(BaseEndpoint):
    PATH = f"{BASE}/providers"

    async def list(
            self,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/providers."""
        params = {k: v for k, v in {
            "limit": limit,
            "offset": offset,
        }.items() if v is not None}
        return await self._http.get(
            self.PATH,
            params=params or None,
            expected_status=expected_status,
            response_model=ProviderCollectionResponse if expected_status == HTTPStatus.OK else None,
        )
