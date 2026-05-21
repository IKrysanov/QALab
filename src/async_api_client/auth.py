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

import asyncio
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
            session: AsyncClient,
            login_url: str = "/login",
            login_field: str = "username",
            password_field: str = "password",
            as_json: bool = False,
    ):
        self._username = username
        self._password = password
        self._login_url = login_url
        self._login_field = login_field
        self._password_field = password_field
        self._as_json = as_json
        self._session = session
        self._logged_in = False
        self._lock = asyncio.Lock()

    async def apply(self, headers: dict) -> dict:
        if not self._logged_in:
            async with self._lock:
                if not self._logged_in:
                    await self._login()
                    self._logged_in = True

        return headers

    async def invalidate(self) -> None:
        async with self._lock:
            self._logged_in = False
            self._session.cookies.clear()

    async def _login(self) -> None:
        payload = {
            self._login_field: self._username,
            self._password_field: self._password,
        }
        if self._as_json:
            response = await self._session.post(self._login_url, json=payload)
        else:
            response = await self._session.post(self._login_url, data=payload)

        assert 200 <= response.status_code < 400, (
            f"Login failed: {response.status_code}, body: {response.text}"
        )

        if not self._session.cookies:
            raise RuntimeError("Login succeeded but no cookies were set by server")


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
