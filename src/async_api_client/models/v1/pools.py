"""Модели для Pool-ресурсов Airflow Stable REST API v1 (Airflow 2.x)."""

from typing import List, Optional

from pydantic import BaseModel


class PoolResponse(BaseModel):
    """Схема Pool из ответа /api/v1.

    Записываемые поля — ``name``, ``slots``, ``description``, ``include_deferred``;
    остальные счётчики ``*_slots`` — readOnly.
    """

    name: Optional[str] = None
    slots: Optional[int] = None
    occupied_slots: Optional[int] = None
    running_slots: Optional[int] = None
    queued_slots: Optional[int] = None
    open_slots: Optional[int] = None
    scheduled_slots: Optional[int] = None
    deferred_slots: Optional[int] = None
    description: Optional[str] = None
    include_deferred: Optional[bool] = None


class PoolCollectionResponse(BaseModel):
    pools: List[PoolResponse]
    total_entries: int


class PoolBody(BaseModel):
    """Тело POST/PATCH /api/v1/pools (схема Pool, записываемые поля)."""

    name: str
    slots: Optional[int] = None
    description: Optional[str] = None
    include_deferred: Optional[bool] = None
