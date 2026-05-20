class APIError(Exception):
    """Сетевые проблемы, не связанные с HTTP-статусом."""


class APITimeoutError(APIError):
    """Таймаут запроса."""