"""Модели для XCom-ресурсов Airflow API v2."""

from typing import Any, List, Optional

from pydantic import BaseModel


class XComResponse(BaseModel):
    key: str
    timestamp: str
    logical_date: Any
    map_index: int
    task_id: str
    dag_id: str
    run_id: str
    dag_display_name: str
    task_display_name: str
    run_after: str
    value: Optional[Any] = None


class XComCollectionResponse(BaseModel):
    xcom_entries: List[XComResponse]
    total_entries: int


class XComCreateBody(BaseModel):
    key: str
    value: Any
    map_index: Optional[int] = None


class XComUpdateBody(BaseModel):
    value: Any
