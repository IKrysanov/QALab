"""Эндпоинты для Connection-ресурсов Airflow Stable REST API v1 (Airflow 2.x).

Базовый префикс ``/api/v1`` задаётся через ``APIConfig.prefix_path``.
"""

from http import HTTPStatus
from typing import Any, List, Optional, Union

from httpx import Response

from ..base import BaseEndpoint
from ...http_client import StatusCode
from ...models.v1.connections import (
    ConnectionBody,
    ConnectionCollectionResponse,
    ConnectionResponse,
    ConnectionTestResponse,
)


class ConnectionsEndpoint(BaseEndpoint):
    """Операции с /api/v1/connections."""

    PATH = "/connections"

    async def list(
            self,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            order_by: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v1/connections."""
        params = {k: v for k, v in {
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
        }.items() if v is not None}
        return await self._http.get(
            self.PATH,
            params=params or None,
            expected_status=expected_status,
            response_model=ConnectionCollectionResponse if expected_status == HTTPStatus.OK else None,
        )

    async def get(
            self,
            connection_id: str,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v1/connections/{connection_id}."""
        return await self._http.get(
            f"{self.PATH}/{connection_id}",
            expected_status=expected_status,
            response_model=ConnectionResponse if expected_status == HTTPStatus.OK else None,
        )

    async def create(
            self,
            payload: Union[ConnectionBody, dict],
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """POST /api/v1/connections (в v1 отвечает 200)."""
        return await self._http.post(
            self.PATH,
            json=payload,
            expected_status=expected_status,
            response_model=ConnectionResponse if expected_status == HTTPStatus.OK else None,
            **kwargs,
        )

    async def patch(
            self,
            connection_id: str,
            payload: Union[ConnectionBody, dict],
            update_mask: Optional[List[str]] = None,
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """PATCH /api/v1/connections/{connection_id}."""
        params = {"update_mask": update_mask} if update_mask else None
        return await self._http.patch(
            f"{self.PATH}/{connection_id}",
            json=payload,
            params=params,
            expected_status=expected_status,
            response_model=ConnectionResponse if expected_status == HTTPStatus.OK else None,
            **kwargs,
        )

    async def delete(
            self,
            connection_id: str,
            expected_status: StatusCode = HTTPStatus.NO_CONTENT,
    ) -> Response:
        """DELETE /api/v1/connections/{connection_id}."""
        return await self._http.delete(
            f"{self.PATH}/{connection_id}",
            expected_status=expected_status,
        )

    async def test(
            self,
            payload: Union[ConnectionBody, dict],
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """POST /api/v1/connections/test — проверить соединение."""
        return await self._http.post(
            f"{self.PATH}/test",
            json=payload,
            expected_status=expected_status,
            response_model=ConnectionTestResponse if expected_status == HTTPStatus.OK else None,
            **kwargs,
        )
