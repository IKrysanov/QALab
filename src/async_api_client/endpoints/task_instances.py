"""Эндпоинты для TaskInstance-ресурсов Airflow API v2.

Покрывает теги: Task Instance, Extra Links, XCom.
Все пути являются под-ресурсами /dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances.
"""

from http import HTTPStatus
from typing import Any, List, Optional, Union

from httpx import Response

from ..endpoints.base import BaseEndpoint
from ..http_client import StatusCode
from ..models.task_instances import (
    BulkTaskInstanceBody,
    ClearTaskInstancesBody,
    ExtraLinkCollectionResponse,
    ExternalLogUrlResponse,
    HITLDetailCollection,
    HITLDetailResponse,
    PatchTaskInstanceBody,
    TaskDependencyCollectionResponse,
    TaskInstanceCollectionResponse,
    TaskInstanceHistoryCollectionResponse,
    TaskInstanceResponse,
    TaskInstancesLogResponse,
    TaskInstancesBatchBody,
    UpdateHITLDetailPayload,
)
from ..models.xcoms import (
    XComCollectionResponse,
    XComCreateBody,
    XComResponse,
    XComUpdateBody,
)


class TaskInstancesEndpoint(BaseEndpoint):
    """Все операции с task instances, logs, xcoms, HITL."""

    def _base(self, dag_id: str, dag_run_id: str) -> str:
        return f"/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances"

    # ------------------------------------------------------------------ #
    #  List / Batch                                                        #
    # ------------------------------------------------------------------ #

    async def list(
            self,
            dag_id: str,
            dag_run_id: str,
            task_id: Optional[str] = None,
            state: Optional[List[str]] = None,
            pool: Optional[str] = None,
            queue: Optional[str] = None,
            executor: Optional[str] = None,
            map_index: Optional[int] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            order_by: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances."""
        params = {k: v for k, v in {
            "task_id": task_id,
            "state": state,
            "pool": pool,
            "queue": queue,
            "executor": executor,
            "map_index": map_index,
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
        }.items() if v is not None}
        return await self._http.get(
            self._base(dag_id, dag_run_id),
            params=params or None,
            expected_status=expected_status,
            response_model=TaskInstanceCollectionResponse if expected_status == HTTPStatus.OK else None,
        )

    async def list_batch(
            self,
            dag_id: str,
            dag_run_id: str,
            payload: Union[TaskInstancesBatchBody, dict],
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """POST .../taskInstances/list — расширенный поиск."""
        return await self._http.post(
            f"{self._base(dag_id, dag_run_id)}/list",
            json=payload,
            expected_status=expected_status,
            response_model=TaskInstanceCollectionResponse if expected_status == HTTPStatus.OK else None,
            **kwargs,
        )

    async def bulk(
            self,
            dag_id: str,
            dag_run_id: str,
            payload: Union[BulkTaskInstanceBody, dict],
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """PATCH .../taskInstances — массовое обновление."""
        return await self._http.patch(
            self._base(dag_id, dag_run_id),
            json=payload,
            expected_status=expected_status,
            **kwargs,
        )

    # ------------------------------------------------------------------ #
    #  Single TaskInstance                                                 #
    # ------------------------------------------------------------------ #

    async def get(
            self,
            dag_id: str,
            dag_run_id: str,
            task_id: str,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET .../taskInstances/{task_id}."""
        return await self._http.get(
            f"{self._base(dag_id, dag_run_id)}/{task_id}",
            expected_status=expected_status,
            response_model=TaskInstanceResponse if expected_status == HTTPStatus.OK else None,
        )

    async def patch(
            self,
            dag_id: str,
            dag_run_id: str,
            task_id: str,
            payload: Union[PatchTaskInstanceBody, dict],
            map_index: Optional[int] = None,
            update_mask: Optional[List[str]] = None,
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """PATCH .../taskInstances/{task_id}."""
        params = {k: v for k, v in {
            "map_index": map_index,
            "update_mask": update_mask,
        }.items() if v is not None}
        return await self._http.patch(
            f"{self._base(dag_id, dag_run_id)}/{task_id}",
            json=payload,
            params=params or None,
            expected_status=expected_status,
            response_model=TaskInstanceResponse if expected_status == HTTPStatus.OK else None,
            **kwargs,
        )

    async def patch_dry_run(
            self,
            dag_id: str,
            dag_run_id: str,
            task_id: str,
            payload: Union[PatchTaskInstanceBody, dict],
            map_index: Optional[int] = None,
            update_mask: Optional[List[str]] = None,
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """PATCH .../taskInstances/{task_id}/dry_run — dry-run обновления."""
        params = {k: v for k, v in {
            "map_index": map_index,
            "update_mask": update_mask,
        }.items() if v is not None}
        return await self._http.patch(
            f"{self._base(dag_id, dag_run_id)}/{task_id}/dry_run",
            json=payload,
            params=params or None,
            expected_status=expected_status,
            **kwargs,
        )

    async def delete(
            self,
            dag_id: str,
            dag_run_id: str,
            task_id: str,
            map_index: Optional[int] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """DELETE .../taskInstances/{task_id}."""
        params = {"map_index": map_index} if map_index is not None else None
        return await self._http.delete(
            f"{self._base(dag_id, dag_run_id)}/{task_id}",
            params=params,
            expected_status=expected_status,
        )

    # ------------------------------------------------------------------ #
    #  Mapped TaskInstance                                                 #
    # ------------------------------------------------------------------ #

    async def get_mapped(
            self,
            dag_id: str,
            dag_run_id: str,
            task_id: str,
            map_index: int,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET .../taskInstances/{task_id}/{map_index}."""
        return await self._http.get(
            f"{self._base(dag_id, dag_run_id)}/{task_id}/{map_index}",
            expected_status=expected_status,
            response_model=TaskInstanceResponse if expected_status == HTTPStatus.OK else None,
        )

    async def list_mapped(
            self,
            dag_id: str,
            dag_run_id: str,
            task_id: str,
            state: Optional[List[str]] = None,
            map_index: Optional[int] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            order_by: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET .../taskInstances/{task_id}/listMapped."""
        params = {k: v for k, v in {
            "state": state,
            "map_index": map_index,
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
        }.items() if v is not None}
        return await self._http.get(
            f"{self._base(dag_id, dag_run_id)}/{task_id}/listMapped",
            params=params or None,
            expected_status=expected_status,
            response_model=TaskInstanceCollectionResponse if expected_status == HTTPStatus.OK else None,
        )

    # ------------------------------------------------------------------ #
    #  Clear (под DAG)                                                     #
    # ------------------------------------------------------------------ #

    async def clear(
            self,
            dag_id: str,
            payload: Union[ClearTaskInstancesBody, dict],
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """POST /api/v2/dags/{dag_id}/clearTaskInstances."""
        return await self._http.post(
            f"{BASE}/dags/{dag_id}/clearTaskInstances",
            json=payload,
            expected_status=expected_status,
            **kwargs,
        )

    # ------------------------------------------------------------------ #
    #  Dependencies                                                        #
    # ------------------------------------------------------------------ #

    async def get_dependencies(
            self,
            dag_id: str,
            dag_run_id: str,
            task_id: str,
            map_index: Optional[int] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET .../taskInstances/{task_id}/dependencies."""
        params = {"map_index": map_index} if map_index is not None else None
        return await self._http.get(
            f"{self._base(dag_id, dag_run_id)}/{task_id}/dependencies",
            params=params,
            expected_status=expected_status,
            response_model=TaskDependencyCollectionResponse if expected_status == HTTPStatus.OK else None,
        )

    # ------------------------------------------------------------------ #
    #  Tries / History                                                     #
    # ------------------------------------------------------------------ #

    async def get_tries(
            self,
            dag_id: str,
            dag_run_id: str,
            task_id: str,
            map_index: Optional[int] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET .../taskInstances/{task_id}/tries."""
        params = {"map_index": map_index} if map_index is not None else None
        return await self._http.get(
            f"{self._base(dag_id, dag_run_id)}/{task_id}/tries",
            params=params,
            expected_status=expected_status,
            response_model=TaskInstanceHistoryCollectionResponse if expected_status == HTTPStatus.OK else None,
        )

    async def get_try_details(
            self,
            dag_id: str,
            dag_run_id: str,
            task_id: str,
            task_try_number: int,
            map_index: Optional[int] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET .../taskInstances/{task_id}/tries/{task_try_number}."""
        params = {"map_index": map_index} if map_index is not None else None
        return await self._http.get(
            f"{self._base(dag_id, dag_run_id)}/{task_id}/tries/{task_try_number}",
            params=params,
            expected_status=expected_status,
        )

    # ------------------------------------------------------------------ #
    #  Logs                                                                #
    # ------------------------------------------------------------------ #

    async def get_log(
            self,
            dag_id: str,
            dag_run_id: str,
            task_id: str,
            try_number: int,
            full_content: Optional[bool] = None,
            map_index: Optional[int] = None,
            token: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET .../taskInstances/{task_id}/logs/{try_number}."""
        params = {k: v for k, v in {
            "full_content": full_content,
            "map_index": map_index,
            "token": token,
        }.items() if v is not None}
        return await self._http.get(
            f"{self._base(dag_id, dag_run_id)}/{task_id}/logs/{try_number}",
            params=params or None,
            expected_status=expected_status,
            response_model=TaskInstancesLogResponse if expected_status == HTTPStatus.OK else None,
        )

    async def get_external_log_url(
            self,
            dag_id: str,
            dag_run_id: str,
            task_id: str,
            try_number: int,
            map_index: Optional[int] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET .../taskInstances/{task_id}/externalLogUrl/{try_number}."""
        params = {"map_index": map_index} if map_index is not None else None
        return await self._http.get(
            f"{self._base(dag_id, dag_run_id)}/{task_id}/externalLogUrl/{try_number}",
            params=params,
            expected_status=expected_status,
            response_model=ExternalLogUrlResponse if expected_status == HTTPStatus.OK else None,
        )

    # ------------------------------------------------------------------ #
    #  Extra Links                                                         #
    # ------------------------------------------------------------------ #

    async def get_extra_links(
            self,
            dag_id: str,
            dag_run_id: str,
            task_id: str,
            map_index: Optional[int] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET .../taskInstances/{task_id}/links."""
        params = {"map_index": map_index} if map_index is not None else None
        return await self._http.get(
            f"{self._base(dag_id, dag_run_id)}/{task_id}/links",
            params=params,
            expected_status=expected_status,
            response_model=ExtraLinkCollectionResponse if expected_status == HTTPStatus.OK else None,
        )

    # ------------------------------------------------------------------ #
    #  XCom                                                                #
    # ------------------------------------------------------------------ #

    async def get_xcom_entries(
            self,
            dag_id: str,
            dag_run_id: str,
            task_id: str,
            xcom_key: Optional[str] = None,
            map_index: Optional[int] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET .../taskInstances/{task_id}/xcomEntries."""
        params = {k: v for k, v in {
            "xcom_key": xcom_key,
            "map_index": map_index,
            "limit": limit,
            "offset": offset,
        }.items() if v is not None}
        return await self._http.get(
            f"{self._base(dag_id, dag_run_id)}/{task_id}/xcomEntries",
            params=params or None,
            expected_status=expected_status,
            response_model=XComCollectionResponse if expected_status == HTTPStatus.OK else None,
        )

    async def get_xcom_entry(
            self,
            dag_id: str,
            dag_run_id: str,
            task_id: str,
            xcom_key: str,
            map_index: Optional[int] = None,
            deserialize: Optional[bool] = None,
            stringify: Optional[bool] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET .../taskInstances/{task_id}/xcomEntries/{xcom_key}."""
        params = {k: v for k, v in {
            "map_index": map_index,
            "deserialize": deserialize,
            "stringify": stringify,
        }.items() if v is not None}
        return await self._http.get(
            f"{self._base(dag_id, dag_run_id)}/{task_id}/xcomEntries/{xcom_key}",
            params=params or None,
            expected_status=expected_status,
            response_model=XComResponse if expected_status == HTTPStatus.OK else None,
        )

    async def create_xcom_entry(
            self,
            dag_id: str,
            dag_run_id: str,
            task_id: str,
            payload: Union[XComCreateBody, dict],
            expected_status: StatusCode = HTTPStatus.CREATED,
            **kwargs: Any,
    ) -> Response:
        """POST .../taskInstances/{task_id}/xcomEntries."""
        return await self._http.post(
            f"{self._base(dag_id, dag_run_id)}/{task_id}/xcomEntries",
            json=payload,
            expected_status=expected_status,
            response_model=XComResponse if expected_status == HTTPStatus.CREATED else None,
            **kwargs,
        )

    async def update_xcom_entry(
            self,
            dag_id: str,
            dag_run_id: str,
            task_id: str,
            xcom_key: str,
            payload: Union[XComUpdateBody, dict],
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """PATCH .../taskInstances/{task_id}/xcomEntries/{xcom_key}."""
        return await self._http.patch(
            f"{self._base(dag_id, dag_run_id)}/{task_id}/xcomEntries/{xcom_key}",
            json=payload,
            expected_status=expected_status,
            response_model=XComResponse if expected_status == HTTPStatus.OK else None,
            **kwargs,
        )

    async def delete_xcom_entry(
            self,
            dag_id: str,
            dag_run_id: str,
            task_id: str,
            xcom_key: str,
            map_index: Optional[int] = None,
            expected_status: StatusCode = HTTPStatus.NO_CONTENT,
    ) -> Response:
        """DELETE .../taskInstances/{task_id}/xcomEntries/{xcom_key}."""
        params = {"map_index": map_index} if map_index is not None else None
        return await self._http.delete(
            f"{self._base(dag_id, dag_run_id)}/{task_id}/xcomEntries/{xcom_key}",
            params=params,
            expected_status=expected_status,
        )

    # ------------------------------------------------------------------ #
    #  HITL (Human-in-the-Loop)                                           #
    # ------------------------------------------------------------------ #

    async def get_hitl_details(
            self,
            dag_id: str,
            dag_run_id: str,
            task_id: Optional[str] = None,
            map_index: Optional[int] = None,
            state: Optional[str] = None,
            response_received: Optional[bool] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            order_by: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/dags/{dag_id}/dagRuns/{dag_run_id}/hitlDetails."""
        params = {k: v for k, v in {
            "task_id": task_id,
            "map_index": map_index,
            "state": state,
            "response_received": response_received,
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
        }.items() if v is not None}
        return await self._http.get(
            f"{BASE}/dags/{dag_id}/dagRuns/{dag_run_id}/hitlDetails",
            params=params or None,
            expected_status=expected_status,
            response_model=HITLDetailCollection if expected_status == HTTPStatus.OK else None,
        )

    async def get_hitl_detail(
            self,
            dag_id: str,
            dag_run_id: str,
            task_id: str,
            map_index: int,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET .../taskInstances/{task_id}/{map_index}/hitlDetails."""
        return await self._http.get(
            f"{self._base(dag_id, dag_run_id)}/{task_id}/{map_index}/hitlDetails",
            expected_status=expected_status,
            response_model=HITLDetailResponse if expected_status == HTTPStatus.OK else None,
        )

    async def update_hitl_detail(
            self,
            dag_id: str,
            dag_run_id: str,
            task_id: str,
            map_index: int,
            payload: Union[UpdateHITLDetailPayload, dict],
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """PATCH .../taskInstances/{task_id}/{map_index}/hitlDetails."""
        return await self._http.patch(
            f"{self._base(dag_id, dag_run_id)}/{task_id}/{map_index}/hitlDetails",
            json=payload,
            expected_status=expected_status,
            response_model=HITLDetailResponse if expected_status == HTTPStatus.OK else None,
            **kwargs,
        )
