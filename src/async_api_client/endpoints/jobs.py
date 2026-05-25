"""Эндпоинты для Job-ресурсов Airflow API v2."""

from http import HTTPStatus
from typing import Optional

from httpx import Response

from ..endpoints.base import BaseEndpoint
from ..http_client import StatusCode
from ..models.monitor import JobCollectionResponse


class JobsEndpoint(BaseEndpoint):
    PATH = "/jobs"

    async def list(
            self,
            is_alive: Optional[bool] = None,
            start_date_gte: Optional[str] = None,
            start_date_lte: Optional[str] = None,
            end_date_gte: Optional[str] = None,
            end_date_lte: Optional[str] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            order_by: Optional[str] = None,
            job_state: Optional[str] = None,
            job_type: Optional[str] = None,
            hostname: Optional[str] = None,
            executor_class: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/jobs."""
        params = {k: v for k, v in {
            "is_alive": is_alive,
            "start_date_gte": start_date_gte,
            "start_date_lte": start_date_lte,
            "end_date_gte": end_date_gte,
            "end_date_lte": end_date_lte,
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
            "job_state": job_state,
            "job_type": job_type,
            "hostname": hostname,
            "executor_class": executor_class,
        }.items() if v is not None}
        return await self._http.get(
            self.PATH,
            params=params or None,
            expected_status=expected_status,
            response_model=JobCollectionResponse if expected_status == HTTPStatus.OK else None,
        )
