"""Модели для Asset-ресурсов Airflow API v2."""

from typing import Any, List, Optional

from pydantic import BaseModel


class AssetAliasResponse(BaseModel):
    id: int
    name: str
    group: str


class AssetAliasCollectionResponse(BaseModel):
    asset_aliases: List[AssetAliasResponse]
    total_entries: int


class AssetWatcherResponse(BaseModel):
    dag_id: str
    created_at: str
    updated_at: str


class AssetResponse(BaseModel):
    id: int
    name: str
    uri: str
    group: str
    extra: Optional[Any] = None
    created_at: str
    updated_at: str
    scheduled_dags: List[Any] = []
    producing_tasks: List[Any] = []
    consuming_tasks: List[Any] = []
    aliases: List[AssetAliasResponse] = []
    watchers: List[AssetWatcherResponse] = []
    last_asset_event: Optional[Any] = None


class AssetCollectionResponse(BaseModel):
    assets: List[AssetResponse]
    total_entries: int


class AssetEventResponse(BaseModel):
    id: int
    asset_id: int
    uri: Optional[str] = None
    name: Optional[str] = None
    group: Optional[str] = None
    extra: Optional[Any] = None
    source_task_id: Optional[str] = None
    source_dag_id: Optional[str] = None
    source_run_id: Optional[str] = None
    source_map_index: int
    created_dagruns: List[Any] = []
    timestamp: str
    partition_key: Optional[str] = None


class AssetEventCollectionResponse(BaseModel):
    asset_events: List[AssetEventResponse]
    total_entries: int


class CreateAssetEventsBody(BaseModel):
    asset_id: int
    partition_key: Optional[str] = None
    extra: Optional[Any] = None


class MaterializeAssetBody(BaseModel):
    logical_date: Optional[str] = None


class QueuedEventResponse(BaseModel):
    uri: str
    dag_id: Optional[str] = None
    created_at: str


class QueuedEventCollectionResponse(BaseModel):
    queued_events: List[QueuedEventResponse]
    total_entries: int
