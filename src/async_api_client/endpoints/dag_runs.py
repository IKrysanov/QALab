"""Эндпоинты для DagRun-ресурсов Airflow API v2."""

from http import HTTPStatus
from typing import Any, List, Optional, Union

from httpx import Response

from ..endpoints.base import BaseEndpoint
from ..http_client import StatusCode
from ..models.dag_runs import (
    DAGRunClearBody,
    DAGRunCollectionResponse,
    DAGRunPatchBody,
    DAGRunResponse,
    DAGRunsBatchBody,
    TriggerDAGRunPostBody,
)


class DagRunsEndpoint(BaseEndpoint):
    """Все операции с /api/v2/dags/{dag_id}/dagRuns."""

    def _path(self, dag_id: str) -> str:
        return "/dags/{dag_id}/dagRuns"

    # ------------------------------------------------------------------ #
    #  List / Batch                                                        #
    # ------------------------------------------------------------------ #

    async def list(
            self,
            dag_id: str,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            run_after_gte: Optional[str] = None,
            run_after_lte: Optional[str] = None,
            logical_date_gte: Optional[str] = None,
            logical_date_lte: Optional[str] = None,
            start_date_gte: Optional[str] = None,
            start_date_lte: Optional[str] = None,
            end_date_gte: Optional[str] = None,
            end_date_lte: Optional[str] = None,
            state: Optional[List[str]] = None,
            run_type: Optional[List[str]] = None,
            order_by: Optional[str] = None,
            run_id_pattern: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/dags/{dag_id}/dagRuns."""
        params = {k: v for k, v in {
            "limit": limit,
            "offset": offset,
            "run_after_gte": run_after_gte,
            "run_after_lte": run_after_lte,
            "logical_date_gte": logical_date_gte,
            "logical_date_lte": logical_date_lte,
            "start_date_gte": start_date_gte,
            "start_date_lte": start_date_lte,
            "end_date_gte": end_date_gte,
            "end_date_lte": end_date_lte,
            "state": state,
            "run_type": run_type,
            "order_by": order_by,
            "run_id_pattern": run_id_pattern,
        }.items() if v is not None}
        return await self._http.get(
            self._path(dag_id),
            params=params or None,
            expected_status=expected_status,
            response_model=DAGRunCollectionResponse if expected_status == HTTPStatus.OK else None,
        )

    async def list_batch(
            self,
            dag_id: str,
            payload: Union[DAGRunsBatchBody, dict],
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """POST /api/v2/dags/{dag_id}/dagRuns/list — расширенный поиск через тело запроса."""
        return await self._http.post(
            f"{self._path(dag_id)}/list",
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
        """POST /api/v2/dags/{dag_id}/dagRuns — запустить DAG."""
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
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/dags/{dag_id}/dagRuns/{dag_run_id}."""
        return await self._http.get(
            f"{self._path(dag_id)}/{dag_run_id}",
            expected_status=expected_status,
            response_model=DAGRunResponse if expected_status == HTTPStatus.OK else None,
        )

    async def patch(
            self,
            dag_id: str,
            dag_run_id: str,
            payload: Union[DAGRunPatchBody, dict],
            update_mask: Optional[List[str]] = None,
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """PATCH /api/v2/dags/{dag_id}/dagRuns/{dag_run_id}."""
        params = {"update_mask": update_mask} if update_mask else None
        return await self._http.patch(
            f"{self._path(dag_id)}/{dag_run_id}",
            json=payload,
            params=params,
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
        """DELETE /api/v2/dags/{dag_id}/dagRuns/{dag_run_id}."""
        return await self._http.delete(
            f"{self._path(dag_id)}/{dag_run_id}",
            expected_status=expected_status,
        )

    # ------------------------------------------------------------------ #
    #  Clear                                                               #
    # ------------------------------------------------------------------ #

    async def clear(
            self,
            dag_id: str,
            dag_run_id: str,
            payload: Union[DAGRunClearBody, dict],
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """POST /api/v2/dags/{dag_id}/dagRuns/{dag_run_id}/clear."""
        return await self._http.post(
            f"{self._path(dag_id)}/{dag_run_id}/clear",
            json=payload,
            expected_status=expected_status,
            **kwargs,
        )

    # ------------------------------------------------------------------ #
    #  Upstream Asset Events                                               #
    # ------------------------------------------------------------------ #

    async def get_upstream_asset_events(
            self,
            dag_id: str,
            dag_run_id: str,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/dags/{dag_id}/dagRuns/{dag_run_id}/upstreamAssetEvents."""
        return await self._http.get(
            f"{self._path(dag_id)}/{dag_run_id}/upstreamAssetEvents",
            expected_status=expected_status,
        )

    # ------------------------------------------------------------------ #
    #  Wait (experimental)                                                 #
    # ------------------------------------------------------------------ #

    async def wait_until_finished(
            self,
            dag_id: str,
            dag_run_id: str,
            interval: Optional[float] = None,
            result: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/dags/{dag_id}/dagRuns/{dag_run_id}/wait — дождаться завершения запуска."""
        params = {k: v for k, v in {
            "interval": interval,
            "result": result,
        }.items() if v is not None}
        return await self._http.get(
            f"{self._path(dag_id)}/{dag_run_id}/wait",
            params=params or None,
            expected_status=expected_status,
            response_model=DAGRunResponse if expected_status == HTTPStatus.OK else None,
        )
