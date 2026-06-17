"""Эндпоинты для Pool-ресурсов Airflow Stable REST API v1 (Airflow 2.x).

Базовый префикс ``/api/v1`` задаётся через ``APIConfig.prefix_path``.
"""

from http import HTTPStatus
from typing import Any, List, Optional, Union

from httpx import Response

from ..base import BaseEndpoint
from ...http_client import StatusCode
from ...models.v1.pools import (
    PoolBody,
    PoolCollectionResponse,
    PoolResponse,
)


class PoolsEndpoint(BaseEndpoint):
    """Операции с /api/v1/pools."""

    PATH = "/pools"

    async def list(
            self,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            order_by: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v1/pools."""
        params = {k: v for k, v in {
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
        }.items() if v is not None}
        return await self._http.get(
            self.PATH,
            params=params or None,
            expected_status=expected_status,
            response_model=PoolCollectionResponse if expected_status == HTTPStatus.OK else None,
        )

    async def get(
            self,
            pool_name: str,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v1/pools/{pool_name}."""
        return await self._http.get(
            f"{self.PATH}/{pool_name}",
            expected_status=expected_status,
            response_model=PoolResponse if expected_status == HTTPStatus.OK else None,
        )

    async def create(
            self,
            payload: Union[PoolBody, dict],
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """POST /api/v1/pools (в v1 отвечает 200)."""
        return await self._http.post(
            self.PATH,
            json=payload,
            expected_status=expected_status,
            response_model=PoolResponse if expected_status == HTTPStatus.OK else None,
            **kwargs,
        )

    async def patch(
            self,
            pool_name: str,
            payload: Union[PoolBody, dict],
            update_mask: Optional[List[str]] = None,
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """PATCH /api/v1/pools/{pool_name}."""
        params = {"update_mask": update_mask} if update_mask else None
        return await self._http.patch(
            f"{self.PATH}/{pool_name}",
            json=payload,
            params=params,
            expected_status=expected_status,
            response_model=PoolResponse if expected_status == HTTPStatus.OK else None,
            **kwargs,
        )

    async def delete(
            self,
            pool_name: str,
            expected_status: StatusCode = HTTPStatus.NO_CONTENT,
    ) -> Response:
        """DELETE /api/v1/pools/{pool_name}."""
        return await self._http.delete(
            f"{self.PATH}/{pool_name}",
            expected_status=expected_status,
        )
