from __future__ import annotations

from typing import Optional, Type

from httpx import AsyncClient
from pydantic import BaseModel

from .config import APIConfig
from .auth import AsyncAuthStrategy
from .http_client import AsyncHTTPClient, HttpxAsyncClient

from .endpoints.v2 import (
    DagsEndpoint,
    DagRunsEndpoint,
    TaskInstancesEndpoint,
    VariablesEndpoint,
    ConnectionsEndpoint,
    PoolsEndpoint,
    AssetsEndpoint,
    BackfillsEndpoint,
    EventLogsEndpoint,
    JobsEndpoint,
    PluginsEndpoint,
    ProvidersEndpoint,
    ImportErrorsEndpoint,
    MonitorEndpoint,
)
from .endpoints.v1 import (
    DagsEndpoint as DagsEndpointV1,
    DagRunsEndpoint as DagRunsEndpointV1,
    TaskInstancesEndpoint as TaskInstancesEndpointV1,
    ConnectionsEndpoint as ConnectionsEndpointV1,
    VariablesEndpoint as VariablesEndpointV1,
    PoolsEndpoint as PoolsEndpointV1,
    MonitorEndpoint as MonitorEndpointV1,
)


def _resolve_api_version(config: APIConfig) -> str:
    """Определить версию набора эндпоинтов по ``APIConfig.prefix_path``.

    ``/api/v1`` → ``"v1"`` (Airflow 2.x), всё остальное (в т.ч. ``/api/v2``)
    → ``"v2"`` (Airflow 3.x, поведение по умолчанию).
    """
    last = config.prefix_path.strip("/").rsplit("/", 1)[-1].lower()
    return "v1" if last == "v1" else "v2"


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

    # Полный набор Airflow 3.x (/api/v2).
    ENDPOINTS_V2 = {
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
    # Airflow 2.x (/api/v1) — DAG, DAGRun, TaskInstance, Connection, Variable, Pool.
    ENDPOINTS_V1 = {
        "dags": DagsEndpointV1,
        "dag_runs": DagRunsEndpointV1,
        "task_instances": TaskInstancesEndpointV1,
        "connections": ConnectionsEndpointV1,
        "variables": VariablesEndpointV1,
        "pools": PoolsEndpointV1,
        "monitor": MonitorEndpointV1,
    }
    # Дефолтный набор (используется при version="v2").
    ENDPOINTS = ENDPOINTS_V2

    # Аннотации для IDE / автодополнения (ресурсы, общие для обеих версий —
    # реальный класс зависит от версии из APIConfig).
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

        # Набор эндпоинтов выбирается по версии API из APIConfig (/api/v1 vs /api/v2).
        self._endpoints = (
            self.ENDPOINTS_V1 if _resolve_api_version(config) == "v1" else self.ENDPOINTS_V2
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

        for name, cls in self._endpoints.items():
            setattr(self, name, cls(self._http, self))

    async def __aenter__(self) -> "AsyncAPIClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()
