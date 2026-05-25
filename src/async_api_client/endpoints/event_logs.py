"""Эндпоинты для Event Log-ресурсов Airflow API v2."""

from http import HTTPStatus
from typing import List, Optional

from httpx import Response

from ..endpoints.base import BaseEndpoint
from ..http_client import StatusCode
from ..models.monitor import (
    EventLogCollectionResponse,
    EventLogResponse,
)


class EventLogsEndpoint(BaseEndpoint):
    PATH = "/eventLogs"

    async def list(
            self,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            order_by: Optional[str] = None,
            dag_id: Optional[str] = None,
            task_id: Optional[str] = None,
            run_id: Optional[str] = None,
            map_index: Optional[int] = None,
            try_number: Optional[int] = None,
            owner: Optional[str] = None,
            event: Optional[str] = None,
            excluded_events: Optional[List[str]] = None,
            included_events: Optional[List[str]] = None,
            before: Optional[str] = None,
            after: Optional[str] = None,
            dag_id_pattern: Optional[str] = None,
            task_id_pattern: Optional[str] = None,
            run_id_pattern: Optional[str] = None,
            owner_pattern: Optional[str] = None,
            event_pattern: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/eventLogs."""
        params = {k: v for k, v in {
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
            "dag_id": dag_id,
            "task_id": task_id,
            "run_id": run_id,
            "map_index": map_index,
            "try_number": try_number,
            "owner": owner,
            "event": event,
            "excluded_events": excluded_events,
            "included_events": included_events,
            "before": before,
            "after": after,
            "dag_id_pattern": dag_id_pattern,
            "task_id_pattern": task_id_pattern,
            "run_id_pattern": run_id_pattern,
            "owner_pattern": owner_pattern,
            "event_pattern": event_pattern,
        }.items() if v is not None}
        return await self._http.get(
            self.PATH,
            params=params or None,
            expected_status=expected_status,
            response_model=EventLogCollectionResponse if expected_status == HTTPStatus.OK else None,
        )

    async def get(
            self,
            event_log_id: int,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/eventLogs/{event_log_id}."""
        return await self._http.get(
            f"{self.PATH}/{event_log_id}",
            expected_status=expected_status,
            response_model=EventLogResponse if expected_status == HTTPStatus.OK else None,
        )
