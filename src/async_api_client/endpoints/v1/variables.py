"""Эндпоинты для Variable-ресурсов Airflow Stable REST API v1 (Airflow 2.x).

Базовый префикс ``/api/v1`` задаётся через ``APIConfig.prefix_path``.
"""

from http import HTTPStatus
from typing import Any, List, Optional, Union

from httpx import Response

from ..base import BaseEndpoint
from ...http_client import StatusCode
from ...models.v1.variables import (
    VariableBody,
    VariableCollectionResponse,
    VariableResponse,
)


class VariablesEndpoint(BaseEndpoint):
    """Операции с /api/v1/variables."""

    PATH = "/variables"

    async def list(
            self,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            order_by: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v1/variables."""
        params = {k: v for k, v in {
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
        }.items() if v is not None}
        return await self._http.get(
            self.PATH,
            params=params or None,
            expected_status=expected_status,
            response_model=VariableCollectionResponse if expected_status == HTTPStatus.OK else None,
        )

    async def get(
            self,
            variable_key: str,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v1/variables/{variable_key}."""
        return await self._http.get(
            f"{self.PATH}/{variable_key}",
            expected_status=expected_status,
            response_model=VariableResponse if expected_status == HTTPStatus.OK else None,
        )

    async def create(
            self,
            payload: Union[VariableBody, dict],
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """POST /api/v1/variables (в v1 отвечает 200)."""
        return await self._http.post(
            self.PATH,
            json=payload,
            expected_status=expected_status,
            response_model=VariableResponse if expected_status == HTTPStatus.OK else None,
            **kwargs,
        )

    async def patch(
            self,
            variable_key: str,
            payload: Union[VariableBody, dict],
            update_mask: Optional[List[str]] = None,
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """PATCH /api/v1/variables/{variable_key}."""
        params = {"update_mask": update_mask} if update_mask else None
        return await self._http.patch(
            f"{self.PATH}/{variable_key}",
            json=payload,
            params=params,
            expected_status=expected_status,
            response_model=VariableResponse if expected_status == HTTPStatus.OK else None,
            **kwargs,
        )

    async def delete(
            self,
            variable_key: str,
            expected_status: StatusCode = HTTPStatus.NO_CONTENT,
    ) -> Response:
        """DELETE /api/v1/variables/{variable_key}."""
        return await self._http.delete(
            f"{self.PATH}/{variable_key}",
            expected_status=expected_status,
        )
