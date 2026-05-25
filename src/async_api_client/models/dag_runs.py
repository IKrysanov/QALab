"""Модели для DagRun-ресурсов Airflow API v2."""

from typing import Any, List, Optional

from pydantic import BaseModel

from .common import DagRunState, DagRunType


class DAGRunResponse(BaseModel):
    dag_run_id: str
    dag_id: str
    logical_date: Any
    queued_at: Any
    start_date: Any
    end_date: Any
    duration: Any
    data_interval_start: Any
    data_interval_end: Any
    run_after: str
    last_scheduling_decision: Any
    run_type: DagRunType
    state: DagRunState
    triggered_by: Any = None
    triggering_user_name: Any = None
    conf: Any = None
    note: Optional[str] = None
    dag_display_name: str
    bundle_version: Optional[str] = None
    partition_key: Optional[str] = None

    model_config = {"populate_by_name": True}


class DAGRunCollectionResponse(BaseModel):
    dag_runs: List[DAGRunResponse]
    total_entries: int


class TriggerDAGRunPostBody(BaseModel):
    logical_date: Any = None
    dag_run_id: Optional[str] = None
    data_interval_start: Any = None
    data_interval_end: Any = None
    run_after: Any = None
    conf: Optional[Any] = None
    note: Optional[str] = None
    partition_key: Optional[str] = None


class DAGRunPatchBody(BaseModel):
    state: Optional[str] = None
    note: Optional[str] = None


class DAGRunClearBody(BaseModel):
    dry_run: bool = True
    only_failed: bool = False
    run_on_latest_version: bool = False


class DAGRunsBatchBody(BaseModel):
    dag_ids: Optional[List[str]] = None
    states: Optional[List[str]] = None
    logical_date_gte: Optional[str] = None
    logical_date_lte: Optional[str] = None
    start_date_gte: Optional[str] = None
    start_date_lte: Optional[str] = None
    end_date_gte: Optional[str] = None
    end_date_lte: Optional[str] = None
    run_id_pattern: Optional[str] = None
    order_by: Optional[str] = None
    limit: Optional[int] = None
    offset: Optional[int] = None
