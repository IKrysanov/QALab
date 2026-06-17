"""Модели для TaskInstance-ресурсов Airflow Stable REST API v1 (Airflow 2.x).

Покрывает теги: Task Instance, Task Instance Dependencies, Extra Links.
"""

from typing import Any, List, Optional

from pydantic import BaseModel

# Возможные состояния таски. В ответах храним строкой (Airflow возвращает и null).
TASK_INSTANCE_STATES = (
    "success", "running", "failed", "upstream_failed", "skipped",
    "up_for_retry", "up_for_reschedule", "queued", "scheduled",
    "deferred", "removed", "restarting", "none",
)
# state для PATCH/обновления (UpdateTaskState)
TASK_INSTANCE_PATCH_STATES = ("success", "failed", "skipped")


class TaskInstanceResponse(BaseModel):
    """Схема TaskInstance из ответа /api/v1."""

    task_id: Optional[str] = None
    task_display_name: Optional[str] = None
    dag_id: Optional[str] = None
    dag_run_id: Optional[str] = None
    execution_date: Any = None
    start_date: Any = None
    end_date: Any = None
    duration: Optional[float] = None
    state: Optional[str] = None
    try_number: Optional[int] = None
    map_index: Optional[int] = None
    max_tries: Optional[int] = None
    hostname: Optional[str] = None
    unixname: Optional[str] = None
    pool: Optional[str] = None
    pool_slots: Optional[int] = None
    queue: Optional[str] = None
    priority_weight: Optional[int] = None
    operator: Optional[str] = None
    queued_when: Optional[str] = None
    pid: Optional[int] = None
    executor: Optional[str] = None
    executor_config: Optional[str] = None
    sla_miss: Any = None
    rendered_map_index: Optional[str] = None
    rendered_fields: Any = None
    trigger: Any = None
    triggerer_job: Any = None
    note: Optional[str] = None

    model_config = {"populate_by_name": True}


class TaskInstanceCollectionResponse(BaseModel):
    task_instances: List[TaskInstanceResponse]
    total_entries: int


class TaskInstanceReference(BaseModel):
    """Краткая ссылка на таску — возвращается операциями clear/setState."""

    task_id: Optional[str] = None
    dag_id: Optional[str] = None
    execution_date: Optional[str] = None
    dag_run_id: Optional[str] = None


class TaskInstanceReferenceCollection(BaseModel):
    task_instances: List[TaskInstanceReference]


class TaskInstanceHistoryResponse(BaseModel):
    task_id: Optional[str] = None
    task_display_name: Optional[str] = None
    dag_id: Optional[str] = None
    dag_run_id: Optional[str] = None
    start_date: Any = None
    end_date: Any = None
    duration: Optional[float] = None
    state: Optional[str] = None
    try_number: Optional[int] = None
    map_index: Optional[int] = None
    max_tries: Optional[int] = None
    hostname: Optional[str] = None
    unixname: Optional[str] = None
    pool: Optional[str] = None
    pool_slots: Optional[int] = None
    queue: Optional[str] = None
    priority_weight: Optional[int] = None
    operator: Optional[str] = None
    queued_when: Optional[str] = None
    pid: Optional[int] = None
    executor: Optional[str] = None
    executor_config: Optional[str] = None


class TaskInstanceHistoryCollectionResponse(BaseModel):
    task_instances_history: List[TaskInstanceHistoryResponse]
    total_entries: int


# --------------------------------------------------------------------------- #
#  Request bodies                                                              #
# --------------------------------------------------------------------------- #

class UpdateTaskInstanceBody(BaseModel):
    """Тело PATCH .../taskInstances/{task_id}[/{map_index}] (UpdateTaskInstance).

    new_state ∈ success | failed | skipped.
    """

    dry_run: Optional[bool] = None
    new_state: Optional[str] = None


class SetTaskInstanceNoteBody(BaseModel):
    """Тело PATCH .../taskInstances/{task_id}[/{map_index}]/setNote."""

    note: str


class UpdateTaskInstancesStateBody(BaseModel):
    """Тело POST /dags/{dag_id}/updateTaskInstancesState (UpdateTaskInstancesState).

    new_state ∈ success | failed | skipped.
    """

    dry_run: Optional[bool] = None
    task_id: Optional[str] = None
    execution_date: Optional[str] = None
    dag_run_id: Optional[str] = None
    include_upstream: Optional[bool] = None
    include_downstream: Optional[bool] = None
    include_future: Optional[bool] = None
    include_past: Optional[bool] = None
    new_state: Optional[str] = None


class ClearTaskInstancesBody(BaseModel):
    """Тело POST /dags/{dag_id}/clearTaskInstances (ClearTaskInstances)."""

    dry_run: bool = True
    task_ids: Optional[List[str]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    only_failed: Optional[bool] = None
    only_running: Optional[bool] = None
    include_subdags: Optional[bool] = None
    include_parentdag: Optional[bool] = None
    reset_dag_runs: Optional[bool] = None
    dag_run_id: Optional[str] = None
    include_upstream: Optional[bool] = None
    include_downstream: Optional[bool] = None
    include_future: Optional[bool] = None
    include_past: Optional[bool] = None


class TaskInstancesBatchBody(BaseModel):
    """Тело POST /dags/~/dagRuns/~/taskInstances/list (ListTaskInstanceForm)."""

    page_offset: Optional[int] = None
    page_limit: Optional[int] = None
    dag_ids: Optional[List[str]] = None
    dag_run_ids: Optional[List[str]] = None
    task_ids: Optional[List[str]] = None
    execution_date_gte: Optional[str] = None
    execution_date_lte: Optional[str] = None
    start_date_gte: Optional[str] = None
    start_date_lte: Optional[str] = None
    end_date_gte: Optional[str] = None
    end_date_lte: Optional[str] = None
    duration_gte: Optional[float] = None
    duration_lte: Optional[float] = None
    state: Optional[List[str]] = None
    pool: Optional[List[str]] = None
    queue: Optional[List[str]] = None
    executor: Optional[List[str]] = None


# --------------------------------------------------------------------------- #
#  Dependencies / Extra links / Logs                                           #
# --------------------------------------------------------------------------- #

class TaskFailedDependency(BaseModel):
    name: Optional[str] = None
    reason: Optional[str] = None


class TaskInstanceDependencyCollectionResponse(BaseModel):
    dependencies: List[TaskFailedDependency]


class ExtraLinkCollectionResponse(BaseModel):
    extra_links: List[Any]


class TaskInstancesLogResponse(BaseModel):
    content: Any = None
    continuation_token: Optional[str] = None
