"""Эндпоинты для Connection-ресурсов Airflow API v2."""

from http import HTTPStatus
from typing import Any, List, Optional, Union

from httpx import Response

from ..endpoints.base import BaseEndpoint
from ..http_client import StatusCode
from ..models.connections import (
    BulkConnectionsBody,
    ConnectionBody,
    ConnectionCollectionResponse,
    ConnectionResponse,
    ConnectionTestResponse,
)


class ConnectionsEndpoint(BaseEndpoint):
    PATH = "/connections"

    async def list(
            self,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            order_by: Optional[str] = None,
            connection_id_pattern: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/connections."""
        params = {k: v for k, v in {
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
            "connection_id_pattern": connection_id_pattern,
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
        """GET /api/v2/connections/{connection_id}."""
        return await self._http.get(
            f"{self.PATH}/{connection_id}",
            expected_status=expected_status,
            response_model=ConnectionResponse if expected_status == HTTPStatus.OK else None,
        )

    async def create(
            self,
            payload: Union[ConnectionBody, dict],
            expected_status: StatusCode = HTTPStatus.CREATED,
            **kwargs: Any,
    ) -> Response:
        """POST /api/v2/connections."""
        return await self._http.post(
            self.PATH,
            json=payload,
            expected_status=expected_status,
            response_model=ConnectionResponse if expected_status == HTTPStatus.CREATED else None,
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
        """PATCH /api/v2/connections/{connection_id}."""
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
        """DELETE /api/v2/connections/{connection_id}."""
        return await self._http.delete(
            f"{self.PATH}/{connection_id}",
            expected_status=expected_status,
        )

    async def bulk(
            self,
            payload: Union[BulkConnectionsBody, dict],
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """PATCH /api/v2/connections — массовые операции."""
        return await self._http.patch(
            self.PATH,
            json=payload,
            expected_status=expected_status,
            **kwargs,
        )

    async def test(
            self,
            payload: Union[ConnectionBody, dict],
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """POST /api/v2/connections/test — проверить соединение."""
        return await self._http.post(
            f"{self.PATH}/test",
            json=payload,
            expected_status=expected_status,
            response_model=ConnectionTestResponse if expected_status == HTTPStatus.OK else None,
            **kwargs,
        )

    async def create_defaults(
            self,
            expected_status: StatusCode = HTTPStatus.NO_CONTENT,
    ) -> Response:
        """POST /api/v2/connections/defaults — создать дефолтные соединения провайдеров."""
        return await self._http.post(
            f"{self.PATH}/defaults",
            expected_status=expected_status,
        )
