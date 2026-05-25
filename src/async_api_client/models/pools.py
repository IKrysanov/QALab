"""Модели для Pool-ресурсов Airflow API v2."""

from typing import Any, List, Optional

from pydantic import BaseModel

from .common import BulkActionOnExistence, BulkActionNotOnExistence


class PoolResponse(BaseModel):
    name: str
    slots: int
    description: Optional[str] = None
    include_deferred: bool
    occupied_slots: int
    running_slots: int
    queued_slots: int
    scheduled_slots: int
    open_slots: int
    deferred_slots: int
    team_name: Optional[str] = None


class PoolCollectionResponse(BaseModel):
    pools: List[PoolResponse]
    total_entries: int


class PoolBody(BaseModel):
    name: str
    slots: int
    description: Optional[str] = None
    include_deferred: bool = False
    team_name: Optional[str] = None


class PoolPatchBody(BaseModel):
    slots: Optional[int] = None
    description: Optional[str] = None
    include_deferred: Optional[bool] = None


class BulkPoolAction(BaseModel):
    action: str  # "create" | "update" | "delete"
    pools: List[PoolBody]
    action_on_existence: Optional[BulkActionOnExistence] = None
    action_not_on_existence: Optional[BulkActionNotOnExistence] = None


class BulkPoolsBody(BaseModel):
    actions: List[BulkPoolAction]
