"""Модели для Connection-ресурсов Airflow API v2."""

from typing import List, Optional

from pydantic import BaseModel, Field

from .common import BulkActionOnExistence, BulkActionNotOnExistence


class ConnectionResponse(BaseModel):
    connection_id: str
    conn_type: str
    description: Optional[str] = None
    host: Optional[str] = None
    login: Optional[str] = None
    # "schema" — зарезервировано в Pydantic; используем alias
    schema_: Optional[str] = Field(None, alias="schema")
    port: Optional[int] = None
    password: Optional[str] = None
    extra: Optional[str] = None
    team_name: Optional[str] = None

    model_config = {"populate_by_name": True}


class ConnectionCollectionResponse(BaseModel):
    connections: List[ConnectionResponse]
    total_entries: int


class ConnectionBody(BaseModel):
    connection_id: str
    conn_type: str
    description: Optional[str] = None
    host: Optional[str] = None
    login: Optional[str] = None
    schema_: Optional[str] = Field(None, alias="schema")
    port: Optional[int] = None
    password: Optional[str] = None
    extra: Optional[str] = None
    team_name: Optional[str] = None

    model_config = {"populate_by_name": True}


class ConnectionTestResponse(BaseModel):
    status: bool
    message: str


class BulkConnectionAction(BaseModel):
    action: str  # "create" | "update" | "delete"
    connections: List[ConnectionBody]
    action_on_existence: Optional[BulkActionOnExistence] = None
    action_not_on_existence: Optional[BulkActionNotOnExistence] = None


class BulkConnectionsBody(BaseModel):
    actions: List[BulkConnectionAction]
