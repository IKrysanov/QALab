"""Модели для DAG-ресурсов Airflow API v2."""

from typing import Any, List, Optional

from pydantic import BaseModel


class DagTagResponse(BaseModel):
    name: str


class DAGResponse(BaseModel):
    dag_id: str
    dag_display_name: str
    is_paused: bool
    is_stale: bool
    fileloc: str
    relative_fileloc: Optional[str] = None
    description: Optional[str] = None
    timetable_summary: Optional[str] = None
    timetable_description: Optional[str] = None
    tags: List[DagTagResponse] = []
    max_active_tasks: int
    max_active_runs: Optional[int] = None
    max_consecutive_failed_dag_runs: int
    has_task_concurrency_limits: bool
    has_import_errors: bool
    owners: List[str] = []
    file_token: str

    model_config = {"populate_by_name": True}


class DAGDetailsResponse(DAGResponse):
    """Расширенная информация о DAG (/dags/{dag_id}/details)."""
    params: Optional[Any] = None
    doc_md: Optional[str] = None
    template_search_path: Optional[Any] = None
    render_template_as_native_obj: Optional[bool] = None


class DAGPatchBody(BaseModel):
    is_paused: bool


class DagTagCollectionResponse(BaseModel):
    tags: List[DagTagResponse]
    total_entries: int


class DAGCollectionResponse(BaseModel):
    dags: List[DAGResponse]
    total_entries: int


class DagStatsStateResponse(BaseModel):
    state: Optional[str] = None
    count: int


class DagStatsResponse(BaseModel):
    dag_id: str
    dag_display_name: str
    stats: List[DagStatsStateResponse]


class DagStatsCollectionResponse(BaseModel):
    dags: List[DagStatsResponse]
    total_entries: int


class DAGWarningResponse(BaseModel):
    dag_id: str
    warning_type: str
    message: str
    timestamp: str


class DAGWarningCollectionResponse(BaseModel):
    dag_warnings: List[DAGWarningResponse]
    total_entries: int


class DagVersionResponse(BaseModel):
    id: str
    version_number: int
    dag_id: str
    bundle_name: Optional[str] = None
    bundle_version: Optional[str] = None
    created_at: str
    dag_display_name: str
    bundle_url: Optional[str] = None


class DAGVersionCollectionResponse(BaseModel):
    dag_versions: List[DagVersionResponse]
    total_entries: int


class DAGSourceResponse(BaseModel):
    dag_id: str
    version_number: Optional[int] = None
    dag_display_name: str
    content: Optional[str] = None


class TaskResponse(BaseModel):
    task_id: Optional[str] = None
    task_display_name: Optional[str] = None
    owner: Optional[str] = None
    operator_name: Optional[str] = None
    pool: Optional[str] = None
    pool_slots: Optional[Any] = None
    queue: Optional[str] = None
    priority_weight: Optional[int] = None
    depends_on_past: bool = False
    wait_for_downstream: bool = False
    retries: Optional[Any] = None
    is_mapped: bool = False
    downstream_task_ids: List[str] = []


class TaskCollectionResponse(BaseModel):
    tasks: List[TaskResponse]
    total_entries: int
