"""Модели для XCom-ресурсов Airflow Stable REST API v1 (Airflow 2.x).

В v1 XCom доступен только на чтение (GET .../taskInstances/{task_id}/xcomEntries).
"""

from typing import Any, List, Optional

from pydantic import BaseModel


class XComCollectionItem(BaseModel):
    key: Optional[str] = None
    timestamp: Optional[str] = None
    execution_date: Optional[str] = None
    map_index: Optional[int] = None
    task_id: Optional[str] = None
    dag_id: Optional[str] = None


class XComResponse(XComCollectionItem):
    """Одна XCom-запись с десериализованным значением."""

    value: Optional[Any] = None


class XComCollectionResponse(BaseModel):
    xcom_entries: List[XComCollectionItem]
    total_entries: int
