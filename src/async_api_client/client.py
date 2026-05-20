from __future__ import annotations

from typing import Optional, Type

from httpx import AsyncClient
from pydantic import BaseModel

from .config import APIConfig
from .auth import AsyncAuthStrategy
from .http_client import AsyncHTTPClient, HttpxAsyncClient

from .endpoints.posts import PostsEndpoint


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
        "posts": PostsEndpoint,
    }

    # Аннотации для IDE и автодополнения. Реальные атрибуты создаются динамически в _register_endpoints.
    posts: PostsEndpoint

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
