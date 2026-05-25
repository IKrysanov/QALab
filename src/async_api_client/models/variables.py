"""Модели для Variable-ресурсов Airflow API v2."""

from typing import Any, List, Optional

from pydantic import BaseModel

from .common import BulkActionOnExistence, BulkActionNotOnExistence


class VariableResponse(BaseModel):
    key: str
    value: str
    description: Optional[str] = None
    is_encrypted: bool
    team_name: Optional[str] = None


class VariableCollectionResponse(BaseModel):
    variables: List[VariableResponse]
    total_entries: int


class VariableBody(BaseModel):
    key: str
    value: Any
    description: Optional[str] = None
    team_name: Optional[str] = None


class BulkVariableAction(BaseModel):
    action: str  # "create" | "update" | "delete"
    variables: List[VariableBody]
    action_on_existence: Optional[BulkActionOnExistence] = None
    action_not_on_existence: Optional[BulkActionNotOnExistence] = None


class BulkVariablesBody(BaseModel):
    actions: List[BulkVariableAction]


class BulkResponse(BaseModel):
    success: List[Any] = []
    errors: List[Any] = []
