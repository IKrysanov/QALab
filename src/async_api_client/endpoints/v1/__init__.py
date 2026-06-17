"""Эндпоинты Airflow 2.x — Stable REST API ``/api/v1``.

Покрыты ресурсы DAG, DAGRun, TaskInstance (+ XCom как подресурс TaskInstance),
Connection, Variable, Pool.
"""

from .dags import DagsEndpoint
from .dag_runs import DagRunsEndpoint
from .task_instances import TaskInstancesEndpoint
from .connections import ConnectionsEndpoint
from .variables import VariablesEndpoint
from .pools import PoolsEndpoint

__all__ = [
    "DagsEndpoint",
    "DagRunsEndpoint",
    "TaskInstancesEndpoint",
    "ConnectionsEndpoint",
    "VariablesEndpoint",
    "PoolsEndpoint",
]
