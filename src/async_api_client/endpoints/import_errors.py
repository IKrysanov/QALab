"""Эндпоинты для Import Error ресурсов Airflow API v2."""

from http import HTTPStatus
from typing import Optional

from httpx import Response

from ..endpoints.base import BaseEndpoint
from ..http_client import StatusCode
from ..models.monitor import ImportErrorCollectionResponse, ImportErrorResponse


class ImportErrorsEndpoint(BaseEndpoint):
    PATH = "/importErrors"

    async def list(
            self,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            order_by: Optional[str] = None,
            filename_pattern: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/importErrors."""
        params = {k: v for k, v in {
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
            "filename_pattern": filename_pattern,
        }.items() if v is not None}
        return await self._http.get(
            self.PATH,
            params=params or None,
            expected_status=expected_status,
            response_model=ImportErrorCollectionResponse if expected_status == HTTPStatus.OK else None,
        )

    async def get(
            self,
            import_error_id: int,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/importErrors/{import_error_id}."""
        return await self._http.get(
            f"{self.PATH}/{import_error_id}",
            expected_status=expected_status,
            response_model=ImportErrorResponse if expected_status == HTTPStatus.OK else None,
        )
