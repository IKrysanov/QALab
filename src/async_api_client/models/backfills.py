"""Модели для Backfill-ресурсов Airflow API v2."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from .common import ReprocessBehavior


class BackfillResponse(BaseModel):
    id: int
    dag_id: str
    from_date: str
    to_date: str
    dag_run_conf: Optional[Any] = None
    is_paused: bool
    reprocess_behavior: ReprocessBehavior
    max_active_runs: int
    created_at: str
    completed_at: Optional[str] = None
    updated_at: str
    dag_display_name: str


class BackfillCollectionResponse(BaseModel):
    backfills: List[BackfillResponse]
    total_entries: int


class BackfillPostBody(BaseModel):
    dag_id: str
    from_date: str
    to_date: str
    run_backwards: bool = False
    dag_run_conf: Optional[Dict[str, Any]] = None
    reprocess_behavior: ReprocessBehavior = ReprocessBehavior.none
    max_active_runs: int = 1
    run_on_latest_version: bool = False


class DryRunBackfillResponse(BaseModel):
    logical_date: str
    run_id: Optional[str] = None
    dag_run_state: Optional[str] = None
    backfill_id: Optional[int] = None
    run_on_latest_version: bool = False


class DryRunBackfillCollectionResponse(BaseModel):
    backfills: List[DryRunBackfillResponse]
    total_entries: int
