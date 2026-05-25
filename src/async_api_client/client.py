from __future__ import annotations

from typing import Optional, Type

from httpx import AsyncClient
from pydantic import BaseModel

from .config import APIConfig
from .auth import AsyncAuthStrategy
from .http_client import AsyncHTTPClient, HttpxAsyncClient

from .endpoints.dags import DagsEndpoint
from .endpoints.dag_runs import DagRunsEndpoint
from .endpoints.task_instances import TaskInstancesEndpoint
from .endpoints.variables import VariablesEndpoint
from .endpoints.connections import ConnectionsEndpoint
from .endpoints.pools import PoolsEndpoint
from .endpoints.assets import AssetsEndpoint
from .endpoints.backfills import BackfillsEndpoint
from .endpoints.event_logs import EventLogsEndpoint
from .endpoints.jobs import JobsEndpoint
from .endpoints.plugins import PluginsEndpoint, ProvidersEndpoint
from .endpoints.import_errors import ImportErrorsEndpoint
from .endpoints.monitor import MonitorEndpoint


class AsyncAPIClient:
    """
    Высокоуровневый асинхронный API-клиент.

    Назначение:
    - Создавать и держать в себе HTTP-клиент-обёртку (`AsyncHTTPClient`);
    - Регистрировать доступные конечные точки (endpoints) как атрибуты экземпляра;
    - Обеспечивать корректное закрытие подключенных ресурсов через `aclose`
      либо через асинхронный контекстный менеджер.

    Использование:
        async with AsyncAPIClient(config, auth=...) as client:
            await client.users.list()

    Атрибуты:
    - ENDPOINTS: маппинг имён -> классы endpoint'ов (Type[BaseEndpoint]).
      Элементы этого словаря преобразуются в атрибуты экземпляра при инициализации.
    - users: статическая аннотация для IDE; реальный атрибут создаётся динамически.
    """

    ENDPOINTS = {
        "dags": DagsEndpoint,
        "dag_runs": DagRunsEndpoint,
        "task_instances": TaskInstancesEndpoint,
        "variables": VariablesEndpoint,
        "connections": ConnectionsEndpoint,
        "pools": PoolsEndpoint,
        "assets": AssetsEndpoint,
        "backfills": BackfillsEndpoint,
        "event_logs": EventLogsEndpoint,
        "jobs": JobsEndpoint,
        "plugins": PluginsEndpoint,
        "providers": ProvidersEndpoint,
        "import_errors": ImportErrorsEndpoint,
        "monitor": MonitorEndpoint,
    }

    # Аннотации для IDE / автодополнения
    dags: DagsEndpoint
    dag_runs: DagRunsEndpoint
    task_instances: TaskInstancesEndpoint
    variables: VariablesEndpoint
    connections: ConnectionsEndpoint
    pools: PoolsEndpoint
    assets: AssetsEndpoint
    backfills: BackfillsEndpoint
    event_logs: EventLogsEndpoint
    jobs: JobsEndpoint
    plugins: PluginsEndpoint
    providers: ProvidersEndpoint
    import_errors: ImportErrorsEndpoint
    monitor: MonitorEndpoint

    def __init__(
            self,
            config: APIConfig,
            auth: Optional[AsyncAuthStrategy] = None,
            session: Optional[AsyncClient] = None,
            http_client: Optional[AsyncHTTPClient] = None,
            error_models: Optional[dict[int, Type[BaseModel]]] = None,
            validate_request: bool = True,
            validate_response: bool = True,
            validate_status: bool = True,
    ):
        self._http: AsyncHTTPClient = http_client or HttpxAsyncClient(
            config,
            auth=auth,
            session=session,
            error_models=error_models,
            validate_request=validate_request,
            validate_response=validate_response,
            validate_status=validate_status,
        )

        try:
            self._register_endpoints()
        except Exception:
            await_close = self._http.aclose()
            del await_close
            raise

        # TODO: client.py — при ошибке в _register_endpoints() сессия не закрывается корректно(сейчас del await_close — заглушка, нужен await).

    def _register_endpoints(self) -> None:
        """
        Регистрирует конечные точки (endpoints) как атрибуты клиента.

        Для каждой пары (name, EndpointClass) в словаре `ENDPOINTS` создаётся
        экземпляр класса конечной точки и присваивается в `self` под именем `name`.
        Конструктор класса конечной точки ожидается в виде:
            EndpointClass(http_client: AsyncHTTPClient, client: AsyncAPIClient)

        После выполнения метода к клиенту можно обращаться через атрибуты,
        например: `client.users`.
        """

        for name, cls in self.ENDPOINTS.items():
            setattr(self, name, cls(self._http, self))

    async def __aenter__(self) -> "AsyncAPIClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()
