"""Эндпоинты для Variable-ресурсов Airflow API v2."""

from http import HTTPStatus
from typing import Any, List, Optional, Union

from httpx import Response

from ..endpoints.base import BaseEndpoint
from ..http_client import StatusCode
from ..models.variables import (
    BulkResponse,
    BulkVariablesBody,
    VariableBody,
    VariableCollectionResponse,
    VariableResponse,
)


class VariablesEndpoint(BaseEndpoint):
    PATH = "/variables"

    async def list(
            self,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            order_by: Optional[str] = None,
            variable_key_pattern: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/variables."""
        params = {k: v for k, v in {
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
            "variable_key_pattern": variable_key_pattern,
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
        """GET /api/v2/variables/{variable_key}."""
        return await self._http.get(
            f"{self.PATH}/{variable_key}",
            expected_status=expected_status,
            response_model=VariableResponse if expected_status == HTTPStatus.OK else None,
        )

    async def create(
            self,
            payload: Union[VariableBody, dict],
            expected_status: StatusCode = HTTPStatus.CREATED,
            **kwargs: Any,
    ) -> Response:
        """POST /api/v2/variables."""
        return await self._http.post(
            self.PATH,
            json=payload,
            expected_status=expected_status,
            response_model=VariableResponse if expected_status == HTTPStatus.CREATED else None,
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
        """PATCH /api/v2/variables/{variable_key}."""
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
        """DELETE /api/v2/variables/{variable_key}."""
        return await self._http.delete(
            f"{self.PATH}/{variable_key}",
            expected_status=expected_status,
        )

    async def bulk(
            self,
            payload: Union[BulkVariablesBody, dict],
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """PATCH /api/v2/variables — массовые операции create/update/delete."""
        return await self._http.patch(
            self.PATH,
            json=payload,
            expected_status=expected_status,
            response_model=BulkResponse if expected_status == HTTPStatus.OK else None,
            **kwargs,
        )
