"""Эндпоинты Airflow 3.x — REST API ``/api/v2``."""

from .dags import DagsEndpoint
from .dag_runs import DagRunsEndpoint
from .task_instances import TaskInstancesEndpoint
from .variables import VariablesEndpoint
from .connections import ConnectionsEndpoint
from .pools import PoolsEndpoint
from .assets import AssetsEndpoint
from .backfills import BackfillsEndpoint
from .event_logs import EventLogsEndpoint
from .jobs import JobsEndpoint
from .plugins import PluginsEndpoint, ProvidersEndpoint
from .import_errors import ImportErrorsEndpoint
from .monitor import MonitorEndpoint

__all__ = [
    "DagsEndpoint",
    "DagRunsEndpoint",
    "TaskInstancesEndpoint",
    "VariablesEndpoint",
    "ConnectionsEndpoint",
    "PoolsEndpoint",
    "AssetsEndpoint",
    "BackfillsEndpoint",
    "EventLogsEndpoint",
    "JobsEndpoint",
    "PluginsEndpoint",
    "ProvidersEndpoint",
    "ImportErrorsEndpoint",
    "MonitorEndpoint",
]
