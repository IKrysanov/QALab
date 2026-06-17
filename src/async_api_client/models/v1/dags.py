"""Модели для DAG-ресурсов Airflow Stable REST API v1 (Airflow 2.x).

Используется AirflowClient'ом главным образом для pause/unpause: единственное
записываемое поле DAG в v1 — ``is_paused``. Остальные поля — readOnly.
"""

from typing import Any, List, Optional

from pydantic import BaseModel


class DAGResponse(BaseModel):
    """Схема DAG из ответа /api/v1 (большинство полей readOnly)."""

    dag_id: Optional[str] = None
    dag_display_name: Optional[str] = None
    root_dag_id: Optional[str] = None
    is_paused: Optional[bool] = None
    is_active: Optional[bool] = None
    is_subdag: Optional[bool] = None
    last_parsed_time: Any = None
    last_pickled: Any = None
    last_expired: Any = None
    scheduler_lock: Optional[bool] = None
    pickle_id: Optional[str] = None
    default_view: Optional[str] = None
    fileloc: Optional[str] = None
    file_token: Optional[str] = None
    owners: Optional[List[str]] = None
    description: Optional[str] = None
    schedule_interval: Any = None
    timetable_description: Optional[str] = None
    tags: Optional[List[Any]] = None
    max_active_tasks: Optional[int] = None
    max_active_runs: Optional[int] = None
    has_task_concurrency_limits: Optional[bool] = None
    has_import_errors: Optional[bool] = None
    next_dagrun: Any = None
    next_dagrun_data_interval_start: Any = None
    next_dagrun_data_interval_end: Any = None
    next_dagrun_create_after: Any = None
    max_consecutive_failed_dag_runs: Optional[int] = None


class DAGCollectionResponse(BaseModel):
    dags: List[DAGResponse]
    total_entries: int


class DAGPatchBody(BaseModel):
    """Тело PATCH /api/v1/dags/{dag_id} — единственное записываемое поле ``is_paused``."""

    is_paused: bool
