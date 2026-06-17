"""Модели для Variable-ресурсов Airflow Stable REST API v1 (Airflow 2.x)."""

from typing import List, Optional

from pydantic import BaseModel


class VariableResponse(BaseModel):
    """Схема Variable из ответа /api/v1 (включает value)."""

    key: str
    value: Optional[str] = None
    description: Optional[str] = None


class VariableCollectionItem(BaseModel):
    """Элемент коллекции /api/v1/variables (без value)."""

    key: str
    description: Optional[str] = None


class VariableCollectionResponse(BaseModel):
    variables: List[VariableCollectionItem]
    total_entries: int


class VariableBody(BaseModel):
    """Тело POST/PATCH /api/v1/variables (схема Variable)."""

    key: str
    value: str
    description: Optional[str] = None
