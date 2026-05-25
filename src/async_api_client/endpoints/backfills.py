"""Эндпоинты для Backfill-ресурсов Airflow API v2."""

from http import HTTPStatus
from typing import Any, Optional, Union

from httpx import Response

from ..endpoints.base import BaseEndpoint
from ..http_client import StatusCode
from ..models.backfills import (
    BackfillCollectionResponse,
    BackfillPostBody,
    BackfillResponse,
    DryRunBackfillCollectionResponse,
)


class BackfillsEndpoint(BaseEndpoint):
    PATH = "/backfills"

    async def list(
            self,
            dag_id: Optional[str] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            order_by: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/backfills."""
        params = {k: v for k, v in {
            "dag_id": dag_id,
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
        }.items() if v is not None}
        return await self._http.get(
            self.PATH,
            params=params or None,
            expected_status=expected_status,
            response_model=BackfillCollectionResponse if expected_status == HTTPStatus.OK else None,
        )

    async def get(
            self,
            backfill_id: int,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/backfills/{backfill_id}."""
        return await self._http.get(
            f"{self.PATH}/{backfill_id}",
            expected_status=expected_status,
            response_model=BackfillResponse if expected_status == HTTPStatus.OK else None,
        )

    async def create(
            self,
            payload: Union[BackfillPostBody, dict],
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """POST /api/v2/backfills — создать backfill."""
        return await self._http.post(
            self.PATH,
            json=payload,
            expected_status=expected_status,
            response_model=BackfillResponse if expected_status == HTTPStatus.OK else None,
            **kwargs,
        )

    async def dry_run(
            self,
            payload: Union[BackfillPostBody, dict],
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """POST /api/v2/backfills/dry_run — предварительный просмотр без создания."""
        return await self._http.post(
            f"{self.PATH}/dry_run",
            json=payload,
            expected_status=expected_status,
            response_model=DryRunBackfillCollectionResponse if expected_status == HTTPStatus.OK else None,
            **kwargs,
        )

    async def cancel(
            self,
            backfill_id: int,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """PUT /api/v2/backfills/{backfill_id}/cancel."""
        return await self._http.put(
            f"{self.PATH}/{backfill_id}/cancel",
            expected_status=expected_status,
            response_model=BackfillResponse if expected_status == HTTPStatus.OK else None,
        )

    async def pause(
            self,
            backfill_id: int,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """PUT /api/v2/backfills/{backfill_id}/pause."""
        return await self._http.put(
            f"{self.PATH}/{backfill_id}/pause",
            expected_status=expected_status,
            response_model=BackfillResponse if expected_status == HTTPStatus.OK else None,
        )

    async def unpause(
            self,
            backfill_id: int,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """PUT /api/v2/backfills/{backfill_id}/unpause."""
        return await self._http.put(
            f"{self.PATH}/{backfill_id}/unpause",
            expected_status=expected_status,
            response_model=BackfillResponse if expected_status == HTTPStatus.OK else None,
        )
