"""Модели для системных ресурсов Airflow API v2 (health, version, config, jobs, plugins)."""

from typing import Any, List, Optional

from pydantic import BaseModel


# === Version ===

class VersionInfo(BaseModel):
    version: str
    git_version: Optional[str] = None


# === Health / Monitor ===

class BaseInfoResponse(BaseModel):
    status: Optional[str] = None
    latest_dag_run_id: Optional[str] = None


class HealthInfoResponse(BaseModel):
    metadatabase: BaseInfoResponse
    scheduler: Any = None
    triggerer: Any = None
    dag_processor: Any = None


# === Config ===

class ConfigOption(BaseModel):
    key: str
    value: str
    section: str
    source: Optional[str] = None
    is_sensitive: Optional[bool] = None


class ConfigSection(BaseModel):
    name: str
    options: List[ConfigOption]


class Config(BaseModel):
    sections: List[ConfigSection]


# === Event Log ===

class EventLogResponse(BaseModel):
    event_log_id: int
    when: str
    dag_id: Optional[str] = None
    task_id: Optional[str] = None
    run_id: Optional[str] = None
    map_index: Optional[int] = None
    try_number: Optional[int] = None
    event: str
    logical_date: Any = None
    owner: Optional[str] = None
    extra: Optional[Any] = None
    dag_display_name: Optional[str] = None
    task_display_name: Optional[str] = None


class EventLogCollectionResponse(BaseModel):
    event_logs: List[EventLogResponse]
    total_entries: int


# === Import Error ===

class ImportErrorResponse(BaseModel):
    import_error_id: int
    timestamp: str
    filename: str
    bundle_name: Optional[str] = None
    stack_trace: str


class ImportErrorCollectionResponse(BaseModel):
    import_errors: List[ImportErrorResponse]
    total_entries: int


# === Job ===

class JobResponse(BaseModel):
    id: int
    dag_id: Optional[str] = None
    state: Optional[str] = None
    job_type: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    latest_heartbeat: Optional[str] = None
    executor_class: Optional[str] = None
    hostname: Optional[str] = None
    unixname: Optional[str] = None
    dag_display_name: Optional[str] = None


class JobCollectionResponse(BaseModel):
    jobs: List[JobResponse]
    total_entries: int


# === Plugin ===

class PluginResponse(BaseModel):
    name: str
    macros: List[Any] = []
    flask_blueprints: List[Any] = []
    fastapi_apps: List[Any] = []
    fastapi_root_middlewares: List[Any] = []
    external_views: List[Any] = []
    react_apps: List[Any] = []
    appbuilder_views: List[Any] = []
    appbuilder_menu_items: List[Any] = []
    global_operator_extra_links: List[Any] = []
    operator_extra_links: List[Any] = []
    source: str
    listeners: List[Any] = []
    timetables: List[Any] = []


class PluginCollectionResponse(BaseModel):
    plugins: List[PluginResponse]
    total_entries: int


class PluginImportErrorResponse(BaseModel):
    filename: str
    stack_trace: str


class PluginImportErrorCollectionResponse(BaseModel):
    import_errors: List[PluginImportErrorResponse]
    total_entries: int


# === Provider ===

class ProviderResponse(BaseModel):
    package_name: str
    description: str
    version: str
    documentation_url: Optional[str] = None


class ProviderCollectionResponse(BaseModel):
    providers: List[ProviderResponse]
    total_entries: int
