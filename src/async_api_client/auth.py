"""
Асинхронные стратегии аутентификации для HTTP-клиентов на основе httpx.

Содержит:
- базовый абстрактный класс AsyncAuthStrategy;
- простые реализации: NoAuth, BearerAuth, APIKeyAuth;
- стратегия на основе сессии с логином: SessionLoginAuth;
- стратегия с ленивым обновлением токена: RefreshableTokenAuth.

Все стратегии реализуют асинхронный метод `apply(headers: dict) -> dict`,
который возвращает обновлённый набор заголовков для запроса.
"""

from abc import ABC, abstractmethod
from typing import Optional

import asyncio
import httpx
from httpx import AsyncClient


class AsyncAuthStrategy(ABC):
    """
    Абстрактный интерфейс асинхронной стратегии аутентификации.

    Реализации должны переопределить метод `apply`, принимающий текущие
    заголовки запроса и возвращающий обновлённые заголовки (включая
    необходимые поля авторизации).
    """

    @abstractmethod
    async def apply(self, headers: dict) -> dict: ...
    # Возвращаемое значение — новый словарь заголовков.


class NoAuth(AsyncAuthStrategy):
    """
    Стратегия без аутентификации — возвращает заголовки без изменений.
    """

    async def apply(self, headers: dict) -> dict:
        return headers


class BearerAuth(AsyncAuthStrategy):
    """
    Добавляет заголовок `Authorization: Bearer <token>`.

    Args:
        token: строка токена доступа.
    """

    def __init__(self, token: str):
        self._token = token

    async def apply(self, headers: dict) -> dict:
        return {**headers, "Authorization": f"Bearer {self._token}"}


class APIKeyAuth(AsyncAuthStrategy):
    """
    Добавляет API-ключ в заголовки под указанным именем.

    Args:
        api_key: значение ключа API.
        header_name: имя заголовка для передачи ключа (по умолчанию "X-API-Key").
    """

    def __init__(self, api_key: str, header_name: str = "X-API-Key"):
        self._api_key = api_key
        self._header_name = header_name

    async def apply(self, headers: dict) -> dict:
        return {**headers, self._header_name: self._api_key}


class SessionLoginAuth(AsyncAuthStrategy):
    """
    Стратегия аутентификации через POST-запрос на endpoint логина и использование cookie.

    Пояснение поведения:
    - Выполняет POST на `login_url` с полями логина; при успехе берёт cookie из ответа и
      сохраняет их в виде строкового заголовка `Cookie`.
    - Кэширует значение cookie в `self._cookie_header` и использует его для
      последующих запросов до тех пор, пока не будет вызван `invalidate`.
    - Использует асинхронный `asyncio.Lock` чтобы предотвратить параллельные попытки логина.
    - Можно передать внешний `httpx.AsyncClient` через `session` — тогда он будет
      использован для логина (не будет закрыт этой стратегией). Если `session` отсутствует,
      стратегия создаёт временный `AsyncClient` для одного запроса.

    Args:
        username: имя пользователя для логина.
        password: пароль.
        login_url: путь или полный URL для POST-запроса логина.
        login_field: имя поля для логина в форме/JSON.
        password_field: имя поля для пароля в форме/JSON.
        as_json: если True — отправлять payload как JSON, иначе как form-data.
        session: опциональный внешний `httpx.AsyncClient` для выполнения запроса логина.
    """

    def __init__(
            self,
            username: str,
            password: str,
            login_url: str = "/login",
            login_field: str = "username",
            password_field: str = "password",
            as_json: bool = False,
            session: Optional[AsyncClient] = None,
    ):
        self._username = username
        self._password = password
        self._login_url = login_url
        self._login_field = login_field
        self._password_field = password_field
        self._as_json = as_json
        self._session = session
        self._cookie_header: Optional[str] = None
        self._lock = asyncio.Lock()

    async def _login(self) -> None:
        """
        Выполняет POST на `self._login_url` и сохраняет cookie в `self._cookie_header`.

        Бросает:
            AssertionError если HTTP-статус вне диапазона [200, 399].
            RuntimeError если ответ успешен, но cookie отсутствуют.
        """

        payload = {
            self._login_field: self._username,
            self._password_field: self._password,
        }

        async def do_login(client: AsyncClient) -> httpx.Response:
            if self._as_json:
                return await client.post(self._login_url, json=payload)
            return await client.post(self._login_url, data=payload)

        if self._session is not None:
            response = await do_login(self._session)
        else:
            async with httpx.AsyncClient() as tmp:
                response = await do_login(tmp)

        assert 200 <= response.status_code < 400, (
            f"Login failed: status {response.status_code}, body: {response.text}"
        )

        cookies = response.cookies
        if not cookies:
            raise RuntimeError("Login succeeded but no cookies were set by server")

        self._cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())

    async def apply(self, headers: dict) -> dict:
        if self._cookie_header is None:
            async with self._lock:
                if self._cookie_header is None:
                    await self._login()

        return {**headers, "Cookie": self._cookie_header}

    async def invalidate(self) -> None:
        """Сбросить кэш cookie — следующий запрос вызовет повторный логин."""

        async with self._lock:
            self._cookie_header = None


class RefreshableTokenAuth(AsyncAuthStrategy):
    """
    Стратегия, берущая токен у асинхронного провайдера при каждом применении.

    Args:
        token_provider: асинхронная вызываемая сущность (корутина без аргументов),
                        возвращающая строковый токен. Например: `async def provider(): ...`
    """

    def __init__(self, token_provider):
        self._token_provider = token_provider

    async def apply(self, headers: dict) -> dict:
        token = await self._token_provider()
        return {**headers, "Authorization": f"Bearer {token}"}
