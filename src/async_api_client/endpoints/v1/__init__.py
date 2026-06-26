"""Эндпоинты Airflow 2.x — Stable REST API ``/api/v1``.

Покрыты ресурсы DAG, DAGRun, TaskInstance (+ XCom как подресурс TaskInstance),
Connection, Variable, Pool, а также мониторинг (health/version).
"""

from .dags import DagsEndpoint
from .dag_runs import DagRunsEndpoint
from .task_instances import TaskInstancesEndpoint
from .connections import ConnectionsEndpoint
from .variables import VariablesEndpoint
from .pools import PoolsEndpoint
from .monitor import MonitorEndpoint

__all__ = [
    "DagsEndpoint",
    "DagRunsEndpoint",
    "TaskInstancesEndpoint",
    "ConnectionsEndpoint",
    "VariablesEndpoint",
    "PoolsEndpoint",
    "MonitorEndpoint",
]
