"""Эндпоинты для Pool-ресурсов Airflow API v2."""

from http import HTTPStatus
from typing import Any, List, Optional, Union

from httpx import Response

from ..endpoints.base import BaseEndpoint
from ..http_client import StatusCode
from ..models.pools import (
    BulkPoolsBody,
    PoolBody,
    PoolCollectionResponse,
    PoolPatchBody,
    PoolResponse,
)


class PoolsEndpoint(BaseEndpoint):
    PATH = "/pools"

    async def list(
            self,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            order_by: Optional[str] = None,
            pool_name_pattern: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/pools."""
        params = {k: v for k, v in {
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
            "pool_name_pattern": pool_name_pattern,
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
        """GET /api/v2/pools/{pool_name}."""
        return await self._http.get(
            f"{self.PATH}/{pool_name}",
            expected_status=expected_status,
            response_model=PoolResponse if expected_status == HTTPStatus.OK else None,
        )

    async def create(
            self,
            payload: Union[PoolBody, dict],
            expected_status: StatusCode = HTTPStatus.CREATED,
            **kwargs: Any,
    ) -> Response:
        """POST /api/v2/pools."""
        return await self._http.post(
            self.PATH,
            json=payload,
            expected_status=expected_status,
            response_model=PoolResponse if expected_status == HTTPStatus.CREATED else None,
            **kwargs,
        )

    async def patch(
            self,
            pool_name: str,
            payload: Union[PoolPatchBody, dict],
            update_mask: Optional[List[str]] = None,
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """PATCH /api/v2/pools/{pool_name}."""
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
        """DELETE /api/v2/pools/{pool_name}."""
        return await self._http.delete(
            f"{self.PATH}/{pool_name}",
            expected_status=expected_status,
        )

    async def bulk(
            self,
            payload: Union[BulkPoolsBody, dict],
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """PATCH /api/v2/pools — массовые операции create/update/delete."""
        return await self._http.patch(
            self.PATH,
            json=payload,
            expected_status=expected_status,
            **kwargs,
        )
