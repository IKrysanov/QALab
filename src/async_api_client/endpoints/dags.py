"""Эндпоинты для DAG-ресурсов Airflow API v2.

Покрывает теги: DAG, DAG Parsing, DagStats, DagSource, DagVersion, DagWarning, Task.
"""

from http import HTTPStatus
from typing import Any, List, Optional, Union

from httpx import Response

from ..endpoints.base import BaseEndpoint
from ..http_client import StatusCode
from ..models.dags import (
    DAGCollectionResponse,
    DAGDetailsResponse,
    DAGPatchBody,
    DAGResponse,
    DAGSourceResponse,
    DAGVersionCollectionResponse,
    DAGWarningCollectionResponse,
    DagStatsCollectionResponse,
    DagTagCollectionResponse,
    DagVersionResponse,
    TaskCollectionResponse,
    TaskResponse,
)


class DagsEndpoint(BaseEndpoint):
    PATH = "/dags"

    # ------------------------------------------------------------------ #
    #  DAG Tag                                                             #
    # ------------------------------------------------------------------ #

    async def get_tags(
            self,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            order_by: Optional[str] = None,
            tag_name_pattern: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/dagTags — список тегов DAG."""
        params = {k: v for k, v in {
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
            "tag_name_pattern": tag_name_pattern,
        }.items() if v is not None}
        return await self._http.get(
            f"{BASE}/dagTags",
            params=params or None,
            expected_status=expected_status,
            response_model=DagTagCollectionResponse if expected_status == HTTPStatus.OK else None,
        )

    # ------------------------------------------------------------------ #
    #  DAG CRUD                                                            #
    # ------------------------------------------------------------------ #

    async def list(
            self,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            tags: Optional[List[str]] = None,
            owners: Optional[List[str]] = None,
            dag_id_pattern: Optional[str] = None,
            dag_display_name_pattern: Optional[str] = None,
            exclude_stale: Optional[bool] = None,
            paused: Optional[bool] = None,
            has_import_errors: Optional[bool] = None,
            last_dag_run_state: Optional[str] = None,
            order_by: Optional[str] = None,
            is_favorite: Optional[bool] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/dags — список DAG."""
        params = {k: v for k, v in {
            "limit": limit,
            "offset": offset,
            "tags": tags,
            "owners": owners,
            "dag_id_pattern": dag_id_pattern,
            "dag_display_name_pattern": dag_display_name_pattern,
            "exclude_stale": exclude_stale,
            "paused": paused,
            "has_import_errors": has_import_errors,
            "last_dag_run_state": last_dag_run_state,
            "order_by": order_by,
            "is_favorite": is_favorite,
        }.items() if v is not None}
        return await self._http.get(
            self.PATH,
            params=params or None,
            expected_status=expected_status,
            response_model=DAGCollectionResponse if expected_status == HTTPStatus.OK else None,
        )

    async def get(
            self,
            dag_id: str,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/dags/{dag_id}."""
        return await self._http.get(
            f"{self.PATH}/{dag_id}",
            expected_status=expected_status,
            response_model=DAGResponse if expected_status == HTTPStatus.OK else None,
        )

    async def get_details(
            self,
            dag_id: str,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/dags/{dag_id}/details."""
        return await self._http.get(
            f"{self.PATH}/{dag_id}/details",
            expected_status=expected_status,
            response_model=DAGDetailsResponse if expected_status == HTTPStatus.OK else None,
        )

    async def patch(
            self,
            dag_id: str,
            payload: Union[DAGPatchBody, dict],
            update_mask: Optional[List[str]] = None,
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """PATCH /api/v2/dags/{dag_id} — обновить (напр. is_paused)."""
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
            update_mask: Optional[List[str]] = None,
            dag_id_pattern: Optional[str] = None,
            paused: Optional[bool] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """PATCH /api/v2/dags — массовое обновление DAG."""
        params = {k: v for k, v in {
            "update_mask": update_mask,
            "dag_id_pattern": dag_id_pattern,
            "paused": paused,
            "limit": limit,
            "offset": offset,
        }.items() if v is not None}
        return await self._http.patch(
            self.PATH,
            json=payload,
            params=params or None,
            expected_status=expected_status,
            **kwargs,
        )

    async def delete(
            self,
            dag_id: str,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """DELETE /api/v2/dags/{dag_id}."""
        return await self._http.delete(
            f"{self.PATH}/{dag_id}",
            expected_status=expected_status,
        )

    # ------------------------------------------------------------------ #
    #  Favorites                                                           #
    # ------------------------------------------------------------------ #

    async def favorite(
            self,
            dag_id: str,
            expected_status: StatusCode = HTTPStatus.NO_CONTENT,
    ) -> Response:
        """POST /api/v2/dags/{dag_id}/favorite."""
        return await self._http.post(
            f"{self.PATH}/{dag_id}/favorite",
            expected_status=expected_status,
        )

    async def unfavorite(
            self,
            dag_id: str,
            expected_status: StatusCode = HTTPStatus.NO_CONTENT,
    ) -> Response:
        """POST /api/v2/dags/{dag_id}/unfavorite."""
        return await self._http.post(
            f"{self.PATH}/{dag_id}/unfavorite",
            expected_status=expected_status,
        )

    # ------------------------------------------------------------------ #
    #  DagStats                                                            #
    # ------------------------------------------------------------------ #

    async def get_stats(
            self,
            dag_ids: Optional[List[str]] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/dagStats."""
        params = {"dag_ids": dag_ids} if dag_ids else None
        return await self._http.get(
            f"{BASE}/dagStats",
            params=params,
            expected_status=expected_status,
            response_model=DagStatsCollectionResponse if expected_status == HTTPStatus.OK else None,
        )

    # ------------------------------------------------------------------ #
    #  DagSource                                                           #
    # ------------------------------------------------------------------ #

    async def get_source(
            self,
            dag_id: str,
            version_number: Optional[int] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/dagSources/{dag_id}."""
        params = {"version_number": version_number} if version_number else None
        return await self._http.get(
            f"{BASE}/dagSources/{dag_id}",
            params=params,
            expected_status=expected_status,
            response_model=DAGSourceResponse if expected_status == HTTPStatus.OK else None,
        )

    # ------------------------------------------------------------------ #
    #  DagVersion                                                          #
    # ------------------------------------------------------------------ #

    async def get_versions(
            self,
            dag_id: str,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            version_number: Optional[int] = None,
            order_by: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/dags/{dag_id}/dagVersions."""
        params = {k: v for k, v in {
            "limit": limit,
            "offset": offset,
            "version_number": version_number,
            "order_by": order_by,
        }.items() if v is not None}
        return await self._http.get(
            f"{self.PATH}/{dag_id}/dagVersions",
            params=params or None,
            expected_status=expected_status,
            response_model=DAGVersionCollectionResponse if expected_status == HTTPStatus.OK else None,
        )

    async def get_version(
            self,
            dag_id: str,
            version_number: int,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/dags/{dag_id}/dagVersions/{version_number}."""
        return await self._http.get(
            f"{self.PATH}/{dag_id}/dagVersions/{version_number}",
            expected_status=expected_status,
            response_model=DagVersionResponse if expected_status == HTTPStatus.OK else None,
        )

    # ------------------------------------------------------------------ #
    #  DagWarning                                                          #
    # ------------------------------------------------------------------ #

    async def get_warnings(
            self,
            dag_id: Optional[str] = None,
            warning_type: Optional[str] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            order_by: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/dagWarnings."""
        params = {k: v for k, v in {
            "dag_id": dag_id,
            "warning_type": warning_type,
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
        }.items() if v is not None}
        return await self._http.get(
            f"{BASE}/dagWarnings",
            params=params or None,
            expected_status=expected_status,
            response_model=DAGWarningCollectionResponse if expected_status == HTTPStatus.OK else None,
        )

    # ------------------------------------------------------------------ #
    #  DAG Parsing                                                         #
    # ------------------------------------------------------------------ #

    async def reparse_file(
            self,
            file_token: str,
            expected_status: StatusCode = HTTPStatus.CREATED,
    ) -> Response:
        """PUT /api/v2/parseDagFile/{file_token} — перепарсить файл DAG."""
        return await self._http.put(
            f"{BASE}/parseDagFile/{file_token}",
            expected_status=expected_status,
        )

    # ------------------------------------------------------------------ #
    #  Task (под-ресурс DAG)                                               #
    # ------------------------------------------------------------------ #

    async def get_tasks(
            self,
            dag_id: str,
            order_by: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/dags/{dag_id}/tasks."""
        params = {"order_by": order_by} if order_by else None
        return await self._http.get(
            f"{self.PATH}/{dag_id}/tasks",
            params=params,
            expected_status=expected_status,
            response_model=TaskCollectionResponse if expected_status == HTTPStatus.OK else None,
        )

    async def get_task(
            self,
            dag_id: str,
            task_id: str,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/dags/{dag_id}/tasks/{task_id}."""
        return await self._http.get(
            f"{self.PATH}/{dag_id}/tasks/{task_id}",
            expected_status=expected_status,
            response_model=TaskResponse if expected_status == HTTPStatus.OK else None,
        )
