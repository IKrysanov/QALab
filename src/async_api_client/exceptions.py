class APIError(Exception):
    """Сетевые проблемы, не связанные с HTTP-статусом."""


class APITransportError(APIError):
    """Сетевые/инфраструктурные проблемы."""


class APITimeoutError(APIError):
    """Таймаут запроса."""


class APIValidationError(APIError):
    """Расхождение с ожиданиями: статус, тело запроса/ответа."""


class StatusAssertionError(APIValidationError):
    """Фактический HTTP-статус не совпал с ожидаемым."""

    def __init__(self, actual: int, expected: list[int], url: str, body: str) -> None:
        self.actual = actual
        self.expected = expected
        self.url = url
        self.body = body
        super().__init__(
            f"Unexpected status code: got {actual}, expected {expected}. "
            f"URL: {url}\nBody: {body}"
        )


class ResponseValidationError(APIValidationError):
    """Тело ответа не соответствует ожидаемой Pydantic-модели или не является JSON."""


class RequestValidationError(APIValidationError):
    """Тело запроса не соответствует переданной request_model."""
