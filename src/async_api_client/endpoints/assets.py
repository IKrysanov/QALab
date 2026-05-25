"""Эндпоинты для Asset-ресурсов Airflow API v2."""

from http import HTTPStatus
from typing import Any, List, Optional, Union

from httpx import Response

from .base import BaseEndpoint
from ..http_client import StatusCode
from ..models.assets import (
    AssetAliasCollectionResponse,
    AssetAliasResponse,
    AssetCollectionResponse,
    AssetEventCollectionResponse,
    AssetEventResponse,
    AssetResponse,
    CreateAssetEventsBody,
    MaterializeAssetBody,
    QueuedEventCollectionResponse,
    QueuedEventResponse,
)


class AssetsEndpoint(BaseEndpoint):
    PATH = "/assets"

    # ------------------------------------------------------------------ #
    #  Assets                                                            #
    # ------------------------------------------------------------------ #

    async def list(
            self,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            name_pattern: Optional[str] = None,
            uri_pattern: Optional[str] = None,
            dag_ids: Optional[List[str]] = None,
            only_active: Optional[bool] = None,
            order_by: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """GET /api/v2/assets."""
        params = {k: v for k, v in {
            "limit": limit,
            "offset": offset,
            "name_pattern": name_pattern,
            "uri_pattern": uri_pattern,
            "dag_ids": dag_ids,
            "only_active": only_active,
            "order_by": order_by,
        }.items() if v is not None}
        return await self._http.get(
            self.PATH,
            params=params or None,
            expected_status=expected_status,
            response_model=AssetCollectionResponse if expected_status == HTTPStatus.OK else None,
            **kwargs
        )

    async def get(
            self,
            asset_id: int,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/assets/{asset_id}."""
        return await self._http.get(
            f"{self.PATH}/{asset_id}",
            expected_status=expected_status,
            response_model=AssetResponse if expected_status == HTTPStatus.OK else None,
        )

    async def materialize(
            self,
            asset_id: int,
            payload: Union[MaterializeAssetBody, dict, None] = None,
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """POST /api/v2/assets/{asset_id}/materialize — запустить материализацию."""
        return await self._http.post(
            f"{self.PATH}/{asset_id}/materialize",
            json=payload,
            expected_status=expected_status,
            **kwargs,
        )

    # ------------------------------------------------------------------ #
    #  Asset Aliases                                                       #
    # ------------------------------------------------------------------ #

    async def list_aliases(
            self,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            name_pattern: Optional[str] = None,
            order_by: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/assets/aliases."""
        params = {k: v for k, v in {
            "limit": limit,
            "offset": offset,
            "name_pattern": name_pattern,
            "order_by": order_by,
        }.items() if v is not None}
        return await self._http.get(
            f"{self.PATH}/aliases",
            params=params or None,
            expected_status=expected_status,
            response_model=AssetAliasCollectionResponse if expected_status == HTTPStatus.OK else None,
        )

    async def get_alias(
            self,
            asset_alias_id: int,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/assets/aliases/{asset_alias_id}."""
        return await self._http.get(
            f"{self.PATH}/aliases/{asset_alias_id}",
            expected_status=expected_status,
            response_model=AssetAliasResponse if expected_status == HTTPStatus.OK else None,
        )

    # ------------------------------------------------------------------ #
    #  Asset Events                                                        #
    # ------------------------------------------------------------------ #

    async def get_events(
            self,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            order_by: Optional[str] = None,
            asset_id: Optional[int] = None,
            source_dag_id: Optional[str] = None,
            source_task_id: Optional[str] = None,
            source_run_id: Optional[str] = None,
            source_map_index: Optional[int] = None,
            name_pattern: Optional[str] = None,
            timestamp_gte: Optional[str] = None,
            timestamp_lte: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/assets/events."""
        params = {k: v for k, v in {
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
            "asset_id": asset_id,
            "source_dag_id": source_dag_id,
            "source_task_id": source_task_id,
            "source_run_id": source_run_id,
            "source_map_index": source_map_index,
            "name_pattern": name_pattern,
            "timestamp_gte": timestamp_gte,
            "timestamp_lte": timestamp_lte,
        }.items() if v is not None}
        return await self._http.get(
            f"{self.PATH}/events",
            params=params or None,
            expected_status=expected_status,
            response_model=AssetEventCollectionResponse if expected_status == HTTPStatus.OK else None,
        )

    async def create_event(
            self,
            payload: Union[CreateAssetEventsBody, dict],
            expected_status: StatusCode = HTTPStatus.OK,
            **kwargs: Any,
    ) -> Response:
        """POST /api/v2/assets/events — вручную создать событие ассета."""
        return await self._http.post(
            f"{self.PATH}/events",
            json=payload,
            expected_status=expected_status,
            response_model=AssetEventResponse if expected_status == HTTPStatus.OK else None,
            **kwargs,
        )

    # ------------------------------------------------------------------ #
    #  Queued Events (Asset)                                               #
    # ------------------------------------------------------------------ #

    async def get_queued_events(
            self,
            asset_id: int,
            before: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/assets/{asset_id}/queuedEvents."""
        params = {"before": before} if before else None
        return await self._http.get(
            f"{self.PATH}/{asset_id}/queuedEvents",
            params=params,
            expected_status=expected_status,
            response_model=QueuedEventCollectionResponse if expected_status == HTTPStatus.OK else None,
        )

    async def delete_queued_events(
            self,
            asset_id: int,
            before: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.NO_CONTENT,
    ) -> Response:
        """DELETE /api/v2/assets/{asset_id}/queuedEvents."""
        params = {"before": before} if before else None
        return await self._http.delete(
            f"{self.PATH}/{asset_id}/queuedEvents",
            params=params,
            expected_status=expected_status,
        )

    # ------------------------------------------------------------------ #
    #  Queued Events (DAG)                                                 #
    # ------------------------------------------------------------------ #

    async def get_dag_queued_events(
            self,
            dag_id: str,
            before: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/dags/{dag_id}/assets/queuedEvents."""
        params = {"before": before} if before else None
        return await self._http.get(
            f"{self.PATH}/dags/{dag_id}/assets/queuedEvents",
            params=params,
            expected_status=expected_status,
            response_model=QueuedEventCollectionResponse if expected_status == HTTPStatus.OK else None,
        )

    async def delete_dag_queued_events(
            self,
            dag_id: str,
            before: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.NO_CONTENT,
    ) -> Response:
        """DELETE /api/v2/dags/{dag_id}/assets/queuedEvents."""
        params = {"before": before} if before else None
        return await self._http.delete(
            f"{self.PATH}/dags/{dag_id}/assets/queuedEvents",
            params=params,
            expected_status=expected_status,
        )

    async def get_dag_asset_queued_event(
            self,
            dag_id: str,
            asset_id: int,
            before: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """GET /api/v2/dags/{dag_id}/assets/{asset_id}/queuedEvents."""
        params = {"before": before} if before else None
        return await self._http.get(
            f"{self.PATH}/dags/{dag_id}/assets/{asset_id}/queuedEvents",
            params=params,
            expected_status=expected_status,
            response_model=QueuedEventResponse if expected_status == HTTPStatus.OK else None,
        )

    async def delete_dag_asset_queued_event(
            self,
            dag_id: str,
            asset_id: int,
            before: Optional[str] = None,
            expected_status: StatusCode = HTTPStatus.NO_CONTENT,
    ) -> Response:
        """DELETE /api/v2/dags/{dag_id}/assets/{asset_id}/queuedEvents."""
        params = {"before": before} if before else None
        return await self._http.delete(
            f"{self.PATH}/dags/{dag_id}/assets/{asset_id}/queuedEvents",
            params=params,
            expected_status=expected_status,
        )
