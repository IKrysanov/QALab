"""Эндпоинты для DagRun-ресурсов Airflow Stable REST API v1 (Airflow 2.x).

Базовый префикс ``/api/v1`` задаётся через ``APIConfig.prefix_path``.
"""

from http import HTTPStatus
from typing import Any, List, Optional, Union

from httpx import Response

from ..base import BaseEndpoint
from ...http_client import StatusCode
from ...models.v1.dag_runs import (
    DAGRunClearBody,
    DAGRunCollectionResponse,
    DAGRunPatchBody,
    DAGRunResponse,
    DAGRunsBatchBody,
    SetDagRunNoteBody,
    TriggerDAGRunPostBody,
)


class DagRunsEndpoint(BaseEndpoint):
    """Операции с /api/v1/dags/{dag_id}/dagRuns и /dags/~/dagRuns."""

    def _path(self, dag_id: str) -> str:
        return f"/dags/{dag_id}/dagRuns"

    # ------------------------------------------------------------------ #
    #  List / Batch                                                        #
    # ------------------------------------------------------------------ #

    async def list(
            self,
            dag_id: str,
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
            state: Optional[List[str]] = None,
            order_by: Optional[str] = None,
            fields: Optional[List[str]] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v1/dags/{dag_id}/dagRuns."""
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
            "state": state,
            "order_by": order_by,
            "fields": fields,
        }.items() if v is not None}
        return await self._http.get(
            self._path(dag_id),
            params=params or None,
            expected_status=expected_status,
            response_model=DAGRunCollectionResponse if expected_status == HTTPStatus.OK else None,
        )

    async def list_batch(
            self,
            payload: Union[DAGRunsBatchBody, dict],
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """POST /api/v1/dags/~/dagRuns/list — кросс-DAG поиск через тело запроса."""
        return await self._http.post(
            "/dags/~/dagRuns/list",
            json=payload,
            expected_status=expected_status,
            response_model=DAGRunCollectionResponse if expected_status == HTTPStatus.OK else None,
            **kwargs,
        )

    # ------------------------------------------------------------------ #
    #  Trigger / Get / Delete / Patch                                      #
    # ------------------------------------------------------------------ #

    async def trigger(
            self,
            dag_id: str,
            payload: Union[TriggerDAGRunPostBody, dict],
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """POST /api/v1/dags/{dag_id}/dagRuns — запустить DAG (в v1 отвечает 200)."""
        return await self._http.post(
            self._path(dag_id),
            json=payload,
            expected_status=expected_status,
            response_model=DAGRunResponse if expected_status == HTTPStatus.OK else None,
            **kwargs,
        )

    async def get(
            self,
            dag_id: str,
            dag_run_id: str,
            fields: Optional[List[str]] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v1/dags/{dag_id}/dagRuns/{dag_run_id}."""
        params = {"fields": fields} if fields else None
        return await self._http.get(
            f"{self._path(dag_id)}/{dag_run_id}",
            params=params,
            expected_status=expected_status,
            response_model=DAGRunResponse if expected_status == HTTPStatus.OK else None,
        )

    async def patch(
            self,
            dag_id: str,
            dag_run_id: str,
            payload: Union[DAGRunPatchBody, dict],
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """PATCH /api/v1/dags/{dag_id}/dagRuns/{dag_run_id} — изменить состояние."""
        return await self._http.patch(
            f"{self._path(dag_id)}/{dag_run_id}",
            json=payload,
            expected_status=expected_status,
            response_model=DAGRunResponse if expected_status == HTTPStatus.OK else None,
            **kwargs,
        )

    async def delete(
            self,
            dag_id: str,
            dag_run_id: str,
            expected_status: StatusCode = HTTPStatus.NO_CONTENT,
    ) -> Response:
        """DELETE /api/v1/dags/{dag_id}/dagRuns/{dag_run_id}."""
        return await self._http.delete(
            f"{self._path(dag_id)}/{dag_run_id}",
            expected_status=expected_status,
        )

    # ------------------------------------------------------------------ #
    #  Clear / Note                                                        #
    # ------------------------------------------------------------------ #

    async def clear(
            self,
            dag_id: str,
            dag_run_id: str,
            payload: Union[DAGRunClearBody, dict],
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """POST /api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/clear.

        При ``dry_run=true`` отвечает TaskInstanceCollection (затронутые таски),
        при ``dry_run=false`` — обновлённым DAGRun. Модель ответа не фиксируем.
        """
        return await self._http.post(
            f"{self._path(dag_id)}/{dag_run_id}/clear",
            json=payload,
            expected_status=expected_status,
            **kwargs,
        )

    async def set_note(
            self,
            dag_id: str,
            dag_run_id: str,
            payload: Union[SetDagRunNoteBody, dict],
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """PATCH /api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/setNote."""
        return await self._http.patch(
            f"{self._path(dag_id)}/{dag_run_id}/setNote",
            json=payload,
            expected_status=expected_status,
            response_model=DAGRunResponse if expected_status == HTTPStatus.OK else None,
            **kwargs,
        )

    # ------------------------------------------------------------------ #
    #  Upstream Dataset Events                                             #
    # ------------------------------------------------------------------ #

    async def get_upstream_dataset_events(
            self,
            dag_id: str,
            dag_run_id: str,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/upstreamDatasetEvents."""
        return await self._http.get(
            f"{self._path(dag_id)}/{dag_run_id}/upstreamDatasetEvents",
            expected_status=expected_status,
        )
