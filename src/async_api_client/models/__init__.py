"""Pydantic-модели для API."""

from .base import (
    ErrorResponse,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    ValidationErrorResponse,
    ServerError,
)

"""Модели для Airflow API v2."""

from .common import (
    DagRunState,
    DagRunType,
    DagRunTriggeredByType,
    TaskInstanceState,
    ReprocessBehavior,
    BulkActionOnExistence,
    BulkActionNotOnExistence,
    TimeDelta,
    HTTPExceptionResponse,
)
from .dags import (
    DAGResponse,
    DAGDetailsResponse,
    DAGCollectionResponse,
    DAGPatchBody,
    DagTagResponse,
    DagTagCollectionResponse,
    DagStatsResponse,
    DagStatsCollectionResponse,
    DAGWarningResponse,
    DAGWarningCollectionResponse,
    DagVersionResponse,
    DAGVersionCollectionResponse,
    DAGSourceResponse,
    TaskResponse,
    TaskCollectionResponse,
)
from .dag_runs import (
    DAGRunResponse,
    DAGRunCollectionResponse,
    TriggerDAGRunPostBody,
    DAGRunPatchBody,
    DAGRunClearBody,
    DAGRunsBatchBody,
)
from .task_instances import (
    TaskInstanceResponse,
    TaskInstanceCollectionResponse,
    TaskInstanceHistoryResponse,
    TaskInstanceHistoryCollectionResponse,
    PatchTaskInstanceBody,
    ClearTaskInstancesBody,
    BulkTaskInstanceBody,
    TaskInstancesBatchBody,
    TaskDependencyResponse,
    TaskDependencyCollectionResponse,
    TaskInstancesLogResponse,
    ExtraLinkCollectionResponse,
    ExternalLogUrlResponse,
    HITLDetailResponse,
    HITLDetailCollection,
    UpdateHITLDetailPayload,
)
from .variables import (
    VariableResponse,
    VariableCollectionResponse,
    VariableBody,
    BulkVariablesBody,
    BulkResponse,
)
from .connections import (
    ConnectionResponse,
    ConnectionCollectionResponse,
    ConnectionBody,
    ConnectionTestResponse,
    BulkConnectionsBody,
)
from .pools import (
    PoolResponse,
    PoolCollectionResponse,
    PoolBody,
    PoolPatchBody,
    BulkPoolsBody,
)
from .assets import (
    AssetResponse,
    AssetCollectionResponse,
    AssetAliasResponse,
    AssetAliasCollectionResponse,
    AssetEventResponse,
    AssetEventCollectionResponse,
    CreateAssetEventsBody,
    MaterializeAssetBody,
    QueuedEventResponse,
    QueuedEventCollectionResponse,
)
from .backfills import (
    BackfillResponse,
    BackfillCollectionResponse,
    BackfillPostBody,
    DryRunBackfillResponse,
    DryRunBackfillCollectionResponse,
)
from .xcoms import (
    XComResponse,
    XComCollectionResponse,
    XComCreateBody,
    XComUpdateBody,
)
from .monitor import (
    VersionInfo,
    HealthInfoResponse,
    Config,
    ConfigOption,
    ConfigSection,
    EventLogResponse,
    EventLogCollectionResponse,
    ImportErrorResponse,
    ImportErrorCollectionResponse,
    JobResponse,
    JobCollectionResponse,
    PluginResponse,
    PluginCollectionResponse,
    PluginImportErrorResponse,
    PluginImportErrorCollectionResponse,
    ProviderResponse,
    ProviderCollectionResponse,
)

__all__ = [
    # Базовые ошибки
    "ErrorResponse",
    "UnauthorizedError",
    "ForbiddenError",
    "NotFoundError",
    "ValidationErrorResponse",
    "ServerError",
    # Common
    "DagRunState", "DagRunType", "DagRunTriggeredByType", "TaskInstanceState",
    "ReprocessBehavior", "BulkActionOnExistence", "BulkActionNotOnExistence",
    "TimeDelta", "HTTPExceptionResponse",
    # DAGs
    "DAGResponse", "DAGDetailsResponse", "DAGCollectionResponse", "DAGPatchBody",
    "DagTagResponse", "DagTagCollectionResponse",
    "DagStatsResponse", "DagStatsCollectionResponse",
    "DAGWarningResponse", "DAGWarningCollectionResponse",
    "DagVersionResponse", "DAGVersionCollectionResponse",
    "DAGSourceResponse", "TaskResponse", "TaskCollectionResponse",
    # DagRuns
    "DAGRunResponse", "DAGRunCollectionResponse", "TriggerDAGRunPostBody",
    "DAGRunPatchBody", "DAGRunClearBody", "DAGRunsBatchBody",
    # Task Instances
    "TaskInstanceResponse", "TaskInstanceCollectionResponse",
    "TaskInstanceHistoryResponse", "TaskInstanceHistoryCollectionResponse",
    "PatchTaskInstanceBody", "ClearTaskInstancesBody", "BulkTaskInstanceBody",
    "TaskInstancesBatchBody", "TaskDependencyResponse", "TaskDependencyCollectionResponse",
    "TaskInstancesLogResponse", "ExtraLinkCollectionResponse", "ExternalLogUrlResponse",
    "HITLDetailResponse", "HITLDetailCollection", "UpdateHITLDetailPayload",
    # Variables
    "VariableResponse", "VariableCollectionResponse", "VariableBody",
    "BulkVariablesBody", "BulkResponse",
    # Connections
    "ConnectionResponse", "ConnectionCollectionResponse", "ConnectionBody",
    "ConnectionTestResponse", "BulkConnectionsBody",
    # Pools
    "PoolResponse", "PoolCollectionResponse", "PoolBody", "PoolPatchBody", "BulkPoolsBody",
    # Assets
    "AssetResponse", "AssetCollectionResponse",
    "AssetAliasResponse", "AssetAliasCollectionResponse",
    "AssetEventResponse", "AssetEventCollectionResponse",
    "CreateAssetEventsBody", "MaterializeAssetBody",
    "QueuedEventResponse", "QueuedEventCollectionResponse",
    # Backfills
    "BackfillResponse", "BackfillCollectionResponse", "BackfillPostBody",
    "DryRunBackfillResponse", "DryRunBackfillCollectionResponse",
    # XComs
    "XComResponse", "XComCollectionResponse", "XComCreateBody", "XComUpdateBody",
    # Monitor / System
    "VersionInfo", "HealthInfoResponse", "Config", "ConfigOption", "ConfigSection",
    "EventLogResponse", "EventLogCollectionResponse",
    "ImportErrorResponse", "ImportErrorCollectionResponse",
    "JobResponse", "JobCollectionResponse",
    "PluginResponse", "PluginCollectionResponse",
    "PluginImportErrorResponse", "PluginImportErrorCollectionResponse",
    "ProviderResponse", "ProviderCollectionResponse",
]
