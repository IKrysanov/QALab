"""Модели Airflow 2.x — Stable REST API ``/api/v1``.

Покрыты DAG, DAGRun, TaskInstance, XCom, Connection, Variable, Pool.
"""

from .dags import (
    DAGResponse,
    DAGCollectionResponse,
    DAGPatchBody,
)
from .dag_runs import (
    DAGRunResponse,
    DAGRunCollectionResponse,
    TriggerDAGRunPostBody,
    DAGRunPatchBody,
    DAGRunClearBody,
    SetDagRunNoteBody,
    DAGRunsBatchBody,
)
from .task_instances import (
    TaskInstanceResponse,
    TaskInstanceCollectionResponse,
    TaskInstanceReference,
    TaskInstanceReferenceCollection,
    TaskInstanceHistoryResponse,
    TaskInstanceHistoryCollectionResponse,
    UpdateTaskInstanceBody,
    SetTaskInstanceNoteBody,
    UpdateTaskInstancesStateBody,
    ClearTaskInstancesBody,
    TaskInstancesBatchBody,
    TaskFailedDependency,
    TaskInstanceDependencyCollectionResponse,
    ExtraLinkCollectionResponse,
    TaskInstancesLogResponse,
)
from .xcoms import (
    XComCollectionItem,
    XComResponse,
    XComCollectionResponse,
)
from .connections import (
    ConnectionCollectionItem,
    ConnectionResponse,
    ConnectionCollectionResponse,
    ConnectionBody,
    ConnectionTestResponse,
)
from .variables import (
    VariableResponse,
    VariableCollectionItem,
    VariableCollectionResponse,
    VariableBody,
)
from .pools import (
    PoolResponse,
    PoolCollectionResponse,
    PoolBody,
)
from .monitor import (
    HealthInfoResponse,
    VersionInfo,
    MetadatabaseStatus,
    SchedulerStatus,
    TriggererStatus,
    DagProcessorStatus,
)

__all__ = [
    # DAGs
    "DAGResponse", "DAGCollectionResponse", "DAGPatchBody",
    # DagRuns
    "DAGRunResponse", "DAGRunCollectionResponse", "TriggerDAGRunPostBody",
    "DAGRunPatchBody", "DAGRunClearBody", "SetDagRunNoteBody", "DAGRunsBatchBody",
    # Task Instances
    "TaskInstanceResponse", "TaskInstanceCollectionResponse",
    "TaskInstanceReference", "TaskInstanceReferenceCollection",
    "TaskInstanceHistoryResponse", "TaskInstanceHistoryCollectionResponse",
    "UpdateTaskInstanceBody", "SetTaskInstanceNoteBody", "UpdateTaskInstancesStateBody",
    "ClearTaskInstancesBody", "TaskInstancesBatchBody",
    "TaskFailedDependency", "TaskInstanceDependencyCollectionResponse",
    "ExtraLinkCollectionResponse", "TaskInstancesLogResponse",
    # XComs
    "XComCollectionItem", "XComResponse", "XComCollectionResponse",
    # Connections
    "ConnectionCollectionItem", "ConnectionResponse", "ConnectionCollectionResponse",
    "ConnectionBody", "ConnectionTestResponse",
    # Variables
    "VariableResponse", "VariableCollectionItem", "VariableCollectionResponse", "VariableBody",
    # Pools
    "PoolResponse", "PoolCollectionResponse", "PoolBody",
    # Monitor (health / version)
    "HealthInfoResponse", "VersionInfo",
    "MetadatabaseStatus", "SchedulerStatus", "TriggererStatus", "DagProcessorStatus",
]
