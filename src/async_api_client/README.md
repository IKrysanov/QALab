# async_api_client `v0.2.0`

Асинхронный HTTP-клиент для тестирования REST API.  
Построен поверх **httpx** + **pydantic**, интегрируется с **pytest-asyncio** и **Allure**.

---

## Содержание

- [Обзор архитектуры](#обзор-архитектуры)
- [Структура модуля](#структура-модуля)
- [Требования и установка](#требования-и-установка)
- [Быстрый старт](#быстрый-старт)
- [Конфигурация](#конфигурация)
- [Аутентификация](#аутентификация)
- [Endpoint'ы](#endpoints)
- [Валидация запросов и ответов](#валидация-запросов-и-ответов)
- [Обработка ошибок и исключения](#обработка-ошибок-и-исключения)
- [Редиректы](#редиректы)
- [Логирование и Allure](#логирование-и-allure)
- [Утилиты для ассертов](#утилиты-для-ассертов)
- [Настройка pytest](#настройка-pytest)
- [Changelog](#changelog)

---

## Обзор архитектуры

```
AsyncAPIClient          ← публичный фасад, держит endpoint'ы как атрибуты
    └── HttpxAsyncClient    ← транспорт: выполняет запросы, валидирует, логирует
            ├── AsyncAuthStrategy   ← подключаемая стратегия авторизации
            ├── validators          ← статус-код, тело запроса/ответа (pydantic)
            ├── RequestLogger       ← лог + Allure-вложения на каждый запрос
            └── RedirectTracker     ← отслеживание цепочки редиректов
```

Клиент разделён на три уровня:

| Уровень | Классы | Зона ответственности |
|---|---|---|
| **Фасад** | `AsyncAPIClient` | регистрация endpoint'ов, жизненный цикл сессии |
| **Транспорт** | `HttpxAsyncClient` | HTTP-запросы, валидация, логирование |
| **Endpoint** | `BaseEndpoint` + наследники | маршруты и бизнес-логика конкретного ресурса |

---

## Структура модуля

```
src/async_api_client/
├── __init__.py          # публичный API, __version__
├── client.py            # AsyncAPIClient — фасад
├── http_client.py       # AsyncHTTPClient (ABC) + HttpxAsyncClient
├── config.py            # BaseHTTPConfig, APIConfig, WebUIConfig
├── auth.py              # стратегии аутентификации
├── validators.py        # статус, тело запроса/ответа
├── redirects.py         # RedirectTracker, RedirectChain, RedirectHop
├── request_logger.py    # RequestLogger
├── exceptions.py        # иерархия исключений
├── types.py             # type aliases
├── constants.py         # DEFAULT_ERROR_MODELS, SENSITIVE_HEADERS, ...
├── asserts.py           # вспомогательные функции-ассерты для тестов
├── endpoints/
│   ├── base.py          # BaseEndpoint
│   └── posts.py         # PostsEndpoint (пример)
└── models/
    ├── base.py          # ErrorResponse, ValidationErrorResponse, ...
    └── posts.py         # Post, PostCreate, PostPatch, Comment
```

---

## Требования и установка

- **Python 3.11+** (разработка велась на 3.13)
- Ключевые зависимости: `httpx`, `pydantic`, `pytest-asyncio`, `allure-pytest`

```bash
pip install -r requirements.txt
```

---

## Быстрый старт

### 1. Создание клиента

```python
from src.async_api_client import AsyncAPIClient, APIConfig

config = APIConfig(host="jsonplaceholder.typicode.com")

async with AsyncAPIClient(config) as client:
    response = await client.posts.list()
    print(response.json())
```

### 2. Переиспользование сессии (рекомендуется для тестов)

Одна `httpx.AsyncClient`-сессия на всю тестовую сессию исключает накладные расходы на TLS-рукопожатие при каждом тесте.

```python
import httpx
from src.async_api_client import AsyncAPIClient, APIConfig

config = APIConfig(host="api.example.com")

async with httpx.AsyncClient(base_url=config.base_url) as session:
    async with AsyncAPIClient(config, session=session) as client:
        response = await client.posts.get(1)
```

### 3. Fixtures в conftest.py

```python
import httpx
import pytest_asyncio
from src.async_api_client import AsyncAPIClient, APIConfig

@pytest.fixture(scope="session")
def api_config():
    return APIConfig(host="jsonplaceholder.typicode.com")

@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def http_session(api_config):
    async with httpx.AsyncClient(base_url=api_config.base_url) as session:
        yield session

@pytest_asyncio.fixture
async def client(api_config, http_session):
    async with AsyncAPIClient(api_config, session=http_session) as c:
        yield c
```

---

## Конфигурация

Все конфиги — **frozen dataclass**, безопасны для хранения на уровне сессии.

### `APIConfig`

Для REST API. По умолчанию выставляет `Accept: application/json`.

```python
from src.async_api_client import APIConfig

config = APIConfig(
    host="api.example.com",        # без схемы — схема задаётся через protocol
    protocol="https",              # "http" | "https", default: "https"
    port=8080,                     # опционально
    prefix_path="/api/v1",         # добавляется к base_url
    timeout=10.0,
    verify_ssl=True,
    follow_redirects=True,
    default_headers={"X-Team": "qa"},
    max_connections=100,
    max_keepalive_connections=20,
    request_trace_id_header="X-TRACE-ID",  # заголовок для X-Request-ID
    max_log_body=4096,             # макс. длина тела в логах
)

print(config.base_url)   # https://api.example.com/api/v1
print(config.root_url)   # https://api.example.com
```

### `WebUIConfig`

Для тестирования веб-приложений через httpx (не API). Таймаут 30 с, браузерные заголовки.

```python
from src.async_api_client import WebUIConfig

config = WebUIConfig(
    host="app.example.com",
    user_agent="Mozilla/5.0 (compatible; QALab/1.0; +tests)",
)
print(config.all_headers)  # default_headers + User-Agent
```

> **Замечание:** передавать схему (`https://`) прямо в `host` нельзя — `__post_init__` выбросит `ValueError`.

---

## Аутентификация

Аутентификация реализована через **Strategy pattern** — достаточно передать нужный объект в `AsyncAPIClient`.

| Класс | Описание |
|---|---|
| `NoAuth` | без авторизации (дефолт) |
| `BearerAuth` | `Authorization: Bearer <token>` |
| `APIKeyAuth` | произвольный заголовок с ключом (`X-API-Key` по умолчанию) |
| `SessionLoginAuth` | POST-логин + cookie-сессия, потокобезопасна |
| `RefreshableTokenAuth` | токен запрашивается у провайдера перед каждым запросом |

```python
from src.async_api_client import BearerAuth, APIKeyAuth, AsyncAPIClient, APIConfig

config = APIConfig(host="api.example.com")

# Bearer token
async with AsyncAPIClient(config, auth=BearerAuth("my-secret-token")) as client:
    ...

# API key в кастомном заголовке
async with AsyncAPIClient(config, auth=APIKeyAuth("key-123", header_name="X-API-Key")) as client:
    ...
```

### SessionLoginAuth — cookie-аутентификация

```python
from src.async_api_client import SessionLoginAuth

auth = SessionLoginAuth(
    username="admin",
    password="secret",
    session=http_session,         # внешний httpx.AsyncClient
    login_url="/auth/login",
    as_json=True,                 # POST как JSON, иначе form-data
)
# Логин выполняется лениво при первом запросе, повторно не вызывается
```

### Своя стратегия

```python
from src.async_api_client import AsyncAuthStrategy

class HMACAuth(AsyncAuthStrategy):
    async def apply(self, headers: dict) -> dict:
        signature = compute_hmac(...)   # ваша логика
        return {**headers, "X-Signature": signature}
```

---

## Endpoint'ы

### Использование существующего

```python
async with AsyncAPIClient(config) as client:
    # GET /posts
    posts = await client.posts.list()

    # GET /posts?userId=1
    user_posts = await client.posts.list(user_id=1)

    # GET /posts/1
    post = await client.posts.get(1)

    # POST /posts
    from src.async_api_client.models.posts import PostCreate
    new_post = await client.posts.create(
        PostCreate(title="Hello", body="World", userId=1)
    )

    # PUT /posts/1
    await client.posts.update(1, {"id": 1, "userId": 1, "title": "New", "body": "Body"})

    # PATCH /posts/1
    await client.posts.patch(1, {"title": "Patched"})

    # DELETE /posts/1
    await client.posts.delete(1)

    # GET /posts/1/comments
    comments = await client.posts.comments(post_id=1)
```

### Добавление нового endpoint'а

```python
# src/async_api_client/endpoints/users.py
from .base import BaseEndpoint
from http import HTTPStatus

class UsersEndpoint(BaseEndpoint):
    PATH = "/users"

    async def list(self):
        return await self._http.get(self.PATH)

    async def get(self, user_id: int):
        return await self._http.get(f"{self.PATH}/{user_id}")
```

```python
# src/async_api_client/client.py
from .endpoints.users import UsersEndpoint

class AsyncAPIClient:
    ENDPOINTS = {
        "posts": PostsEndpoint,
        "users": UsersEndpoint,   # ← добавить сюда
    }
    users: UsersEndpoint          # ← аннотация для IDE
```

---

## Валидация запросов и ответов

Управление валидацией — на трёх уровнях: клиент → метод endpoint'а → конкретный вызов `request()`.

### Флаги валидации

| Флаг | Описание |
|---|---|
| `validate_request` | сериализует Pydantic-модель; при `dict`-payload — валидирует через `request_model` |
| `validate_response` | валидирует тело ответа через `response_model` или реестр `error_models` |
| `validate_status` | поднимает `StatusAssertionError` при несовпадении статуса |

```python
# Глобально на уровне клиента
AsyncAPIClient(config, validate_response=False)

# Переопределение на уровне одного запроса
await client.posts.create(payload, validate_request=True)
```

### Стратегия валидации ответа

```
request() вызван с response_model
    → строгая валидация (любой статус)

request() без response_model + статус 4xx/5xx
    → мягкая валидация через DEFAULT_ERROR_MODELS
       (нет в реестре → пропуск; не совпало → warning в лог)

request() без response_model + статус 2xx/3xx
    → ResponseValidationError
       (validate_response=True требует явной модели)
```

### Модели ошибок по умолчанию

| Статус | Модель |
|---|---|
| 400 | `ErrorResponse` |
| 401 | `UnauthorizedError` |
| 403 | `ForbiddenError` |
| 404 | `NotFoundError` |
| 409 | `ErrorResponse` |
| 422 | `ValidationErrorResponse` |
| 500, 502, 503, 504 | `ServerError` |

Подменить реестр — через параметр `error_models` конструктора `AsyncAPIClient`.

---

## Обработка ошибок и исключения

```
APIError
├── APITransportError      — сетевые/инфраструктурные проблемы
├── APITimeoutError        — таймаут запроса
└── APIValidationError
    ├── StatusAssertionError       — фактический статус ≠ ожидаемому
    ├── ResponseValidationError    — тело ответа не совпало с моделью
    └── RequestValidationError     — тело запроса не прошло валидацию
```

```python
from src.async_api_client import APITimeoutError, StatusAssertionError
from src.async_api_client.exceptions import ResponseValidationError

try:
    response = await client.posts.get(9999)
except StatusAssertionError as e:
    print(f"Got {e.actual}, expected {e.expected}, url={e.url}")
except APITimeoutError:
    print("Request timed out")
```

---

## Редиректы

Клиент автоматически отслеживает цепочки редиректов и прикладывает их к Allure-отчёту.

```python
from src.async_api_client.asserts import get_redirect_chain, assert_no_redirects

response = await client.posts.list()
assert_no_redirects(response)

# Или вручную
chain = get_redirect_chain(response)
print(chain.count)       # количество хопов
print(chain.final_url)   # итоговый URL
print(chain.status_codes) # [301, 302, ...]

for hop in chain:
    print(hop)  # "GET /old → [301] → /new"
```

---

## Логирование и Allure

Каждый запрос автоматически:
- логирует `→ request` и `← response` в стандартный logger `async_api_client`;
- прикладывает к Allure: **Request**, **Response**, **cURL**-команду;
- маскирует чувствительные заголовки (`Authorization`, `Cookie`, `X-API-Key`, ...)
  и поля тела (`password`, `token`, `secret`, ...);
- обрезает тело до `max_log_body` байт (по умолчанию 4096).

Настройка уровня логирования:

```python
import logging
logging.getLogger("async_api_client").setLevel(logging.DEBUG)
```

---

## Утилиты для ассертов

Модуль `asserts.py` предоставляет готовые Allure-обёрнутые проверки:

```python
from src.async_api_client.asserts import (
    assert_status_code,
    assert_json_has_keys,
    assert_field_equals,
    assert_response_time_below,
    assert_no_redirects,
    assert_redirect_count,
    assert_final_url,
    assert_redirect_status,
)

response = await client.posts.get(1)

assert_status_code(response, 200)
assert_json_has_keys(response, ["id", "title", "body", "userId"])
assert_field_equals(response.json(), "userId", 1)
assert_response_time_below(response, ms=500)
assert_no_redirects(response)
```

---

## Настройка pytest

`pytest.ini` в корне проекта:

```ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = session
asyncio_default_test_loop_scope = session
```
Запуск тестов:

```bash
pytest tests/ --base_url=https://jsonplaceholder.typicode.com -v
```

Запуск с Allure-отчётом:

```bash
pytest tests/ --base_url=https://jsonplaceholder.typicode.com --alluredir=allure-results
allure serve allure-results
```

---

## Changelog

### v0.2.0
- Добавлен `RequestLogger` — изолированное логирование с Allure-вложениями и маскировкой секретов
- Добавлен `RedirectTracker` / `RedirectChain` / `RedirectHop` — отслеживание и ассерты для редиректов
- Добавлен `asserts.py` — набор Allure-обёрнутых функций для проверок в тестах
- Добавлены `WebUIConfig` и `BaseHTTPConfig`
- Добавлены `RefreshableTokenAuth` и `SessionLoginAuth` с lazy-логином и double-checked locking
- Добавлены `SENSITIVE_HEADERS` / `SENSITIVE_BODY_KEYS` — маскировка в логах
- Добавлены `IDEMPOTENT_METHODS` / `RETRYABLE_STATUSES` в константы
- Добавлен `request_trace_id_header` — трассировочный заголовок на каждый запрос
- Реализована трёхуровневая валидация (клиент / endpoint / вызов) с флагами `validate_request`, `validate_response`, `validate_status`
- Реализована мягкая валидация error-тел через `DEFAULT_ERROR_MODELS`
- Иерархия исключений: `APIError` → `APITransportError`, `APITimeoutError`, `APIValidationError` и наследники
- Все конфиги стали `frozen dataclass`
- Полный `__all__` и `__version__ = "0.2.0"` в `__init__.py`
