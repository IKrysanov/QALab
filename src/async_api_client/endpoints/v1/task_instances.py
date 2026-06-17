"""Эндпоинты для TaskInstance-ресурсов Airflow Stable REST API v1 (Airflow 2.x).

Покрывает теги: Task Instance, Task Instance Dependencies, Extra Links, XCom.
Базовый префикс ``/api/v1`` задаётся через ``APIConfig.prefix_path``.
"""

from http import HTTPStatus
from typing import Any, List, Optional, Union

from httpx import Response

from ..base import BaseEndpoint
from ...http_client import StatusCode
from ...models.v1.task_instances import (
    ClearTaskInstancesBody,
    ExtraLinkCollectionResponse,
    SetTaskInstanceNoteBody,
    TaskInstanceCollectionResponse,
    TaskInstanceDependencyCollectionResponse,
    TaskInstanceHistoryCollectionResponse,
    TaskInstanceHistoryResponse,
    TaskInstanceReference,
    TaskInstanceReferenceCollection,
    TaskInstanceResponse,
    TaskInstancesBatchBody,
    TaskInstancesLogResponse,
    UpdateTaskInstanceBody,
    UpdateTaskInstancesStateBody,
)
from ...models.v1.xcoms import XComCollectionResponse, XComResponse


class TaskInstancesEndpoint(BaseEndpoint):
    """Операции с task instances, tries, logs, xcoms, dependencies, extra links."""

    def _base(self, dag_id: str, dag_run_id: str) -> str:
        return f"/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances"

    # ------------------------------------------------------------------ #
    #  List / Batch                                                        #
    # ------------------------------------------------------------------ #

    async def list(
            self,
            dag_id: str,
            dag_run_id: str,
            execution_date_gte: Optional[str] = None,
            execution_date_lte: Optional[str] = None,
            start_date_gte: Optional[str] = None,
            start_date_lte: Optional[str] = None,
            end_date_gte: Optional[str] = None,
            end_date_lte: Optional[str] = None,
            updated_at_gte: Optional[str] = None,
            updated_at_lte: Optional[str] = None,
            duration_gte: Optional[float] = None,
            duration_lte: Optional[float] = None,
            state: Optional[List[str]] = None,
            pool: Optional[List[str]] = None,
            queue: Optional[List[str]] = None,
            executor: Optional[List[str]] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances."""
        params = {k: v for k, v in {
            "execution_date_gte": execution_date_gte,
            "execution_date_lte": execution_date_lte,
            "start_date_gte": start_date_gte,
            "start_date_lte": start_date_lte,
            "end_date_gte": end_date_gte,
            "end_date_lte": end_date_lte,
            "updated_at_gte": updated_at_gte,
            "updated_at_lte": updated_at_lte,
            "duration_gte": duration_gte,
            "duration_lte": duration_lte,
            "state": state,
            "pool": pool,
            "queue": queue,
            "executor": executor,
            "limit": limit,
            "offset": offset,
        }.items() if v is not None}
        return await self._http.get(
            self._base(dag_id, dag_run_id),
            params=params or None,
            expected_status=expected_status,
            response_model=TaskInstanceCollectionResponse if expected_status == HTTPStatus.OK else None,
        )

    async def list_batch(
            self,
            payload: Union[TaskInstancesBatchBody, dict],
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """POST /api/v1/dags/~/dagRuns/~/taskInstances/list — кросс-DAG поиск."""
        return await self._http.post(
            "/dags/~/dagRuns/~/taskInstances/list",
            json=payload,
            expected_status=expected_status,
            response_model=TaskInstanceCollectionResponse if expected_status == HTTPStatus.OK else None,
            **kwargs,
        )

    # ------------------------------------------------------------------ #
    #  Single / Mapped TaskInstance                                        #
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
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            execution_date_gte: Optional[str] = None,
            execution_date_lte: Optional[str] = None,
            start_date_gte: Optional[str] = None,
            start_date_lte: Optional[str] = None,
            end_date_gte: Optional[str] = None,
            end_date_lte: Optional[str] = None,
            updated_at_gte: Optional[str] = None,
            updated_at_lte: Optional[str] = None,
            duration_gte: Optional[float] = None,
            duration_lte: Optional[float] = None,
            state: Optional[List[str]] = None,
            pool: Optional[List[str]] = None,
            queue: Optional[List[str]] = None,
            executor: Optional[List[str]] = None,
            order_by: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET .../taskInstances/{task_id}/listMapped — список mapped-инстансов."""
        params = {k: v for k, v in {
            "limit": limit,
            "offset": offset,
            "execution_date_gte": execution_date_gte,
            "execution_date_lte": execution_date_lte,
            "start_date_gte": start_date_gte,
            "start_date_lte": start_date_lte,
            "end_date_gte": end_date_gte,
            "end_date_lte": end_date_lte,
            "updated_at_gte": updated_at_gte,
            "updated_at_lte": updated_at_lte,
            "duration_gte": duration_gte,
            "duration_lte": duration_lte,
            "state": state,
            "pool": pool,
            "queue": queue,
            "executor": executor,
            "order_by": order_by,
        }.items() if v is not None}
        return await self._http.get(
            f"{self._base(dag_id, dag_run_id)}/{task_id}/listMapped",
            params=params or None,
            expected_status=expected_status,
            response_model=TaskInstanceCollectionResponse if expected_status == HTTPStatus.OK else None,
        )

    async def patch(
            self,
            dag_id: str,
            dag_run_id: str,
            task_id: str,
            payload: Union[UpdateTaskInstanceBody, dict],
            map_index: Optional[int] = None,
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """PATCH .../taskInstances/{task_id}[/{map_index}] — изменить состояние таски.

        Если передан ``map_index`` — используется путь с map_index в URL.
        """
        suffix = f"/{task_id}/{map_index}" if map_index is not None else f"/{task_id}"
        return await self._http.patch(
            f"{self._base(dag_id, dag_run_id)}{suffix}",
            json=payload,
            expected_status=expected_status,
            response_model=TaskInstanceReference if expected_status == HTTPStatus.OK else None,
            **kwargs,
        )

    async def set_note(
            self,
            dag_id: str,
            dag_run_id: str,
            task_id: str,
            payload: Union[SetTaskInstanceNoteBody, dict],
            map_index: Optional[int] = None,
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """PATCH .../taskInstances/{task_id}[/{map_index}]/setNote."""
        suffix = f"/{task_id}/{map_index}" if map_index is not None else f"/{task_id}"
        return await self._http.patch(
            f"{self._base(dag_id, dag_run_id)}{suffix}/setNote",
            json=payload,
            expected_status=expected_status,
            response_model=TaskInstanceResponse if expected_status == HTTPStatus.OK else None,
            **kwargs,
        )

    # ------------------------------------------------------------------ #
    #  Clear / Update state (под DAG)                                      #
    # ------------------------------------------------------------------ #

    async def clear(
            self,
            dag_id: str,
            payload: Union[ClearTaskInstancesBody, dict],
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """POST /api/v1/dags/{dag_id}/clearTaskInstances."""
        return await self._http.post(
            f"/dags/{dag_id}/clearTaskInstances",
            json=payload,
            expected_status=expected_status,
            response_model=TaskInstanceReferenceCollection if expected_status == HTTPStatus.OK else None,
            **kwargs,
        )

    async def update_state(
            self,
            dag_id: str,
            payload: Union[UpdateTaskInstancesStateBody, dict],
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """POST /api/v1/dags/{dag_id}/updateTaskInstancesState."""
        return await self._http.post(
            f"/dags/{dag_id}/updateTaskInstancesState",
            json=payload,
            expected_status=expected_status,
            response_model=TaskInstanceReferenceCollection if expected_status == HTTPStatus.OK else None,
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
        """GET .../taskInstances/{task_id}[/{map_index}]/dependencies."""
        suffix = f"/{task_id}/{map_index}" if map_index is not None else f"/{task_id}"
        return await self._http.get(
            f"{self._base(dag_id, dag_run_id)}{suffix}/dependencies",
            expected_status=expected_status,
            response_model=TaskInstanceDependencyCollectionResponse if expected_status == HTTPStatus.OK else None,
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
    #  Tries / History                                                     #
    # ------------------------------------------------------------------ #

    async def get_tries(
            self,
            dag_id: str,
            dag_run_id: str,
            task_id: str,
            map_index: Optional[int] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            order_by: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET .../taskInstances/{task_id}[/{map_index}]/tries."""
        suffix = f"/{task_id}/{map_index}" if map_index is not None else f"/{task_id}"
        params = {k: v for k, v in {
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
        }.items() if v is not None}
        return await self._http.get(
            f"{self._base(dag_id, dag_run_id)}{suffix}/tries",
            params=params or None,
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
        """GET .../taskInstances/{task_id}[/{map_index}]/tries/{task_try_number}."""
        suffix = f"/{task_id}/{map_index}" if map_index is not None else f"/{task_id}"
        return await self._http.get(
            f"{self._base(dag_id, dag_run_id)}{suffix}/tries/{task_try_number}",
            expected_status=expected_status,
            response_model=TaskInstanceHistoryResponse if expected_status == HTTPStatus.OK else None,
        )

    # ------------------------------------------------------------------ #
    #  Logs                                                                #
    # ------------------------------------------------------------------ #

    async def get_log(
            self,
            dag_id: str,
            dag_run_id: str,
            task_id: str,
            task_try_number: int,
            full_content: Optional[bool] = None,
            map_index: Optional[int] = None,
            token: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET .../taskInstances/{task_id}/logs/{task_try_number}."""
        params = {k: v for k, v in {
            "full_content": full_content,
            "map_index": map_index,
            "token": token,
        }.items() if v is not None}
        return await self._http.get(
            f"{self._base(dag_id, dag_run_id)}/{task_id}/logs/{task_try_number}",
            params=params or None,
            expected_status=expected_status,
            response_model=TaskInstancesLogResponse if expected_status == HTTPStatus.OK else None,
        )

    # ------------------------------------------------------------------ #
    #  XCom (read-only в v1)                                               #
    # ------------------------------------------------------------------ #

    async def get_xcom_entries(
            self,
            dag_id: str,
            dag_run_id: str,
            task_id: str,
            map_index: Optional[int] = None,
            xcom_key: Optional[str] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET .../taskInstances/{task_id}/xcomEntries."""
        params = {k: v for k, v in {
            "map_index": map_index,
            "xcom_key": xcom_key,
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
