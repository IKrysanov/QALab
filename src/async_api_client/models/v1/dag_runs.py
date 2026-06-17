"""Модели для DagRun-ресурсов Airflow Stable REST API v1 (Airflow 2.x)."""

from typing import Any, List, Optional

from pydantic import BaseModel

# Допустимые значения берём из спека, но в ответах храним строкой —
# реальный Airflow может вернуть статус/тип, которого нет в нашем перечне.
DAG_RUN_STATES = ("queued", "running", "success", "failed")
DAG_RUN_TYPES = ("backfill", "manual", "scheduled", "dataset_triggered")
# state для PATCH (UpdateDagRunState)
DAG_RUN_PATCH_STATES = ("success", "failed", "queued")


class DAGRunResponse(BaseModel):
    """Схема DAGRun из ответа /api/v1."""

    dag_run_id: Optional[str] = None
    dag_id: Optional[str] = None
    logical_date: Any = None
    execution_date: Any = None
    start_date: Any = None
    end_date: Any = None
    data_interval_start: Any = None
    data_interval_end: Any = None
    last_scheduling_decision: Any = None
    run_type: Optional[str] = None
    state: Optional[str] = None
    external_trigger: Optional[bool] = None
    conf: Any = None
    note: Optional[str] = None

    model_config = {"populate_by_name": True}


class DAGRunCollectionResponse(BaseModel):
    dag_runs: List[DAGRunResponse]
    total_entries: int


class TriggerDAGRunPostBody(BaseModel):
    """Тело POST /dags/{dag_id}/dagRuns — запуск DAG (схема DAGRun, writable-поля)."""

    dag_run_id: Optional[str] = None
    logical_date: Optional[str] = None
    execution_date: Optional[str] = None
    data_interval_start: Optional[str] = None
    data_interval_end: Optional[str] = None
    conf: Optional[Any] = None
    note: Optional[str] = None


class DAGRunPatchBody(BaseModel):
    """Тело PATCH /dags/{dag_id}/dagRuns/{dag_run_id} (UpdateDagRunState).

    state ∈ success | failed | queued.
    """

    state: Optional[str] = None


class DAGRunClearBody(BaseModel):
    """Тело POST /dags/{dag_id}/dagRuns/{dag_run_id}/clear (ClearDagRun)."""

    dry_run: bool = True


class SetDagRunNoteBody(BaseModel):
    """Тело PATCH /dags/{dag_id}/dagRuns/{dag_run_id}/setNote (SetDagRunNote)."""

    note: str


class DAGRunsBatchBody(BaseModel):
    """Тело POST /dags/~/dagRuns/list (ListDagRunsForm) — кросс-DAG поиск."""

    order_by: Optional[str] = None
    page_offset: Optional[int] = None
    page_limit: Optional[int] = None
    dag_ids: Optional[List[str]] = None
    states: Optional[List[str]] = None
    execution_date_gte: Optional[str] = None
    execution_date_lte: Optional[str] = None
    start_date_gte: Optional[str] = None
    start_date_lte: Optional[str] = None
    end_date_gte: Optional[str] = None
    end_date_lte: Optional[str] = None
