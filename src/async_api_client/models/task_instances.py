"""Модели для TaskInstance-ресурсов Airflow API v2."""

from typing import Any, List, Optional

from pydantic import BaseModel

from .common import TaskInstanceState, BulkActionOnExistence, BulkActionNotOnExistence


class TaskInstanceResponse(BaseModel):
    id: str
    task_id: str
    dag_id: str
    dag_run_id: str
    map_index: int
    logical_date: Any
    run_after: str
    start_date: Any
    end_date: Any
    duration: Any
    state: Any
    try_number: int
    max_tries: int
    task_display_name: str
    dag_display_name: str
    hostname: Any
    unixname: Any
    pool: str
    pool_slots: int
    queue: Any
    priority_weight: Optional[int] = None
    operator: Optional[str] = None
    operator_name: Optional[str] = None
    queued_when: Any = None
    pid: Any = None
    executor: Any = None
    note: Any = None
    rendered_map_index: Any = None

    model_config = {"populate_by_name": True}


class TaskInstanceCollectionResponse(BaseModel):
    task_instances: List[TaskInstanceResponse]
    total_entries: int


class TaskInstanceHistoryResponse(BaseModel):
    task_id: str
    dag_id: str
    dag_run_id: str
    map_index: int
    try_number: int
    start_date: Any
    end_date: Any
    duration: Any
    state: Any
    hostname: Any
    unixname: Any
    pool: str
    pool_slots: int
    queue: Any
    operator: Optional[str] = None


class TaskInstanceHistoryCollectionResponse(BaseModel):
    task_instances: List[TaskInstanceHistoryResponse]
    total_entries: int


class PatchTaskInstanceBody(BaseModel):
    new_state: Optional[str] = None
    note: Optional[str] = None
    include_upstream: bool = False
    include_downstream: bool = False
    include_future: bool = False
    include_past: bool = False


class ClearTaskInstancesBody(BaseModel):
    dry_run: bool = True
    dag_run_id: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    task_ids: Optional[List[str]] = None
    include_subdags: Optional[bool] = None
    include_parentdag: Optional[bool] = None
    reset_dag_runs: Optional[bool] = None
    only_failed: Optional[bool] = None
    only_running: Optional[bool] = None
    include_upstream: Optional[bool] = None
    include_downstream: Optional[bool] = None
    include_future: Optional[bool] = None
    include_past: Optional[bool] = None


class BulkTaskInstanceBody(BaseModel):
    """Тело для /bulk операций над task instances."""
    new_state: Optional[str] = None
    note: Optional[str] = None
    task_ids: Optional[List[str]] = None


class TaskInstancesBatchBody(BaseModel):
    dag_ids: Optional[List[str]] = None
    dag_run_ids: Optional[List[str]] = None
    task_ids: Optional[List[str]] = None
    states: Optional[List[str]] = None
    logical_date_gte: Optional[str] = None
    logical_date_lte: Optional[str] = None
    start_date_gte: Optional[str] = None
    start_date_lte: Optional[str] = None
    end_date_gte: Optional[str] = None
    end_date_lte: Optional[str] = None
    duration_gte: Optional[float] = None
    duration_lte: Optional[float] = None
    pool: Optional[List[str]] = None
    queue: Optional[List[str]] = None
    executor: Optional[List[str]] = None
    limit: Optional[int] = None
    offset: Optional[int] = None
    order_by: Optional[str] = None


class TaskDependencyResponse(BaseModel):
    name: str
    reason: str
    passed: bool


class TaskDependencyCollectionResponse(BaseModel):
    dependencies: List[TaskDependencyResponse]


class TaskInstancesLogResponse(BaseModel):
    content: Any
    continuation_token: Optional[str] = None


class ExtraLinkCollectionResponse(BaseModel):
    extra_links: List[Any]


class ExternalLogUrlResponse(BaseModel):
    url: str


class HITLDetailResponse(BaseModel):
    responded_by: Any
    responded_at: str
    chosen_options: List[Any]
    params_input: Any = None


class HITLDetailCollection(BaseModel):
    hitl_details: List[Any]
    total_entries: int


class UpdateHITLDetailPayload(BaseModel):
    chosen_options: List[str]
    params_input: Optional[Any] = None
