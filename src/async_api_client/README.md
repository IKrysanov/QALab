# QALab — API client для тестирования API с поддержкой асинхронности и стратегий аутентификации.

Кратко: репозиторий содержит асинхронный высокоуровневый API‑клиент (`src/async_api_client`) с поддержкой стратегий аутентификации, обёрткой над httpx и набором endpoint'ов, а также конфигурацию для запуска асинхронных тестов через `pytest`/`pytest-asyncio`.

## Содержание
- `src/async_api_client` — клиент, конфигурация и стратегии аутентификации
- `conftest.py` — pytest fixtures: `http_session`, `session_auth`, `api_client`
- `pytest.ini` — рекомендуемая настройка `asyncio_mode = auto`

## Требования
- `Python 3.11+` (в проекте использовалась `3.13`)
- `pip`
- Рекомендуемые зависимости:
  - `httpx`
  - `pytest`
  - `pytest-asyncio`
  - `anyio`
  - `asyncio`
  - `pydantic`

Установить зависимости:
```bash
pip install -r requirements.txt
```

## Быстрая настройка pytest
В корне проекта добавьте/обновите pytest.ini:
```ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = session
asyncio_default_test_loop_scope = session
```