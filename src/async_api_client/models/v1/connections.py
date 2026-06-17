"""Модели для Connection-ресурсов Airflow Stable REST API v1 (Airflow 2.x)."""

from typing import List, Optional

from pydantic import BaseModel, Field


class ConnectionCollectionItem(BaseModel):
    """Элемент коллекции /api/v1/connections (без password/extra)."""

    connection_id: str
    conn_type: str
    description: Optional[str] = None
    host: Optional[str] = None
    login: Optional[str] = None
    # "schema" зарезервировано в Pydantic — используем alias.
    schema_: Optional[str] = Field(None, alias="schema")
    port: Optional[int] = None

    model_config = {"populate_by_name": True}


class ConnectionResponse(ConnectionCollectionItem):
    """Полная схема Connection из ответа /api/v1 (с extra; password — writeOnly)."""

    password: Optional[str] = None
    extra: Optional[str] = None


class ConnectionCollectionResponse(BaseModel):
    connections: List[ConnectionCollectionItem]
    total_entries: int


class ConnectionBody(ConnectionResponse):
    """Тело POST/PATCH /api/v1/connections (схема Connection)."""


class ConnectionTestResponse(BaseModel):
    status: bool
    message: str
