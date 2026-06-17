"""Эндпоинты для DAG-ресурсов Airflow Stable REST API v1 (Airflow 2.x).

Базовый префикс ``/api/v1`` задаётся через ``APIConfig.prefix_path``.
В v1 единственное записываемое поле DAG — ``is_paused`` (pause/unpause).
"""

from http import HTTPStatus
from typing import Any, List, Optional, Union

from httpx import Response

from ..base import BaseEndpoint
from ...http_client import StatusCode
from ...models.v1.dags import (
    DAGCollectionResponse,
    DAGPatchBody,
    DAGResponse,
)


class DagsEndpoint(BaseEndpoint):
    """Операции с /api/v1/dags."""

    PATH = "/dags"

    async def list(
            self,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            order_by: Optional[str] = None,
            tags: Optional[List[str]] = None,
            only_active: Optional[bool] = None,
            paused: Optional[bool] = None,
            dag_id_pattern: Optional[str] = None,
            fields: Optional[List[str]] = None,
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """GET /api/v1/dags."""
        params = {k: v for k, v in {
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
            "tags": tags,
            "only_active": only_active,
            "paused": paused,
            "dag_id_pattern": dag_id_pattern,
            "fields": fields,
        }.items() if v is not None}
        return await self._http.get(
            self.PATH,
            params=params or None,
            expected_status=expected_status,
            response_model=DAGCollectionResponse if expected_status == HTTPStatus.OK else None,
            **kwargs,
        )

    async def get(
            self,
            dag_id: str,
            fields: Optional[List[str]] = None,
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """GET /api/v1/dags/{dag_id}."""
        params = {"fields": fields} if fields else None
        return await self._http.get(
            f"{self.PATH}/{dag_id}",
            params=params,
            expected_status=expected_status,
            response_model=DAGResponse if expected_status == HTTPStatus.OK else None,
            **kwargs,
        )

    async def patch(
            self,
            dag_id: str,
            payload: Union[DAGPatchBody, dict],
            update_mask: Optional[List[str]] = None,
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """PATCH /api/v1/dags/{dag_id} — pause/unpause (is_paused)."""
        params = {"update_mask": update_mask} if update_mask else None
        return await self._http.patch(
            f"{self.PATH}/{dag_id}",
            json=payload,
            params=params,
            expected_status=expected_status,
            response_model=DAGResponse if expected_status == HTTPStatus.OK else None,
            **kwargs,
        )

    async def patch_many(
            self,
            payload: Union[DAGPatchBody, dict],
            dag_id_pattern: str,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            tags: Optional[List[str]] = None,
            only_active: Optional[bool] = None,
            update_mask: Optional[List[str]] = None,
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """PATCH /api/v1/dags — массовый pause/unpause по ``dag_id_pattern``."""
        params = {k: v for k, v in {
            "dag_id_pattern": dag_id_pattern,
            "limit": limit,
            "offset": offset,
            "tags": tags,
            "only_active": only_active,
            "update_mask": update_mask,
        }.items() if v is not None}
        return await self._http.patch(
            self.PATH,
            json=payload,
            params=params,
            expected_status=expected_status,
            response_model=DAGCollectionResponse if expected_status == HTTPStatus.OK else None,
            **kwargs,
        )

    async def delete(
            self,
            dag_id: str,
            expected_status: StatusCode = HTTPStatus.NO_CONTENT,
    ) -> Response:
        """DELETE /api/v1/dags/{dag_id}."""
        return await self._http.delete(
            f"{self.PATH}/{dag_id}",
            expected_status=expected_status,
        )
