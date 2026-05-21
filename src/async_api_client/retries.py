from typing import Optional, Iterable
import random

from .constants import RETRYABLE_STATUSES, IDEMPOTENT_METHODS
from .exceptions import APITimeoutError, APITransportError


class RetryPolicy:
    """Политика ретраев с экспоненциальным backoff и jitter."""

    DEFAULT_RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
        APITimeoutError,
        APITransportError,
    )

    def __init__(
            self,
            max_attempts: int = 3,
            base_delay: float = 0.5,
            max_delay: float = 10.0,
            jitter: float = 0.25,
            retryable_statuses: Iterable[int] = RETRYABLE_STATUSES,
            retryable_methods: Iterable[str] = IDEMPOTENT_METHODS,
            retryable_exceptions: Optional[tuple[type[BaseException], ...]] = None,
    ) -> None:
        self.max_attempts = max(1, max_attempts)
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self.retryable_statuses = frozenset(retryable_statuses)
        self.retryable_methods = frozenset(m.upper() for m in retryable_methods)
        self.retryable_exceptions = (
            retryable_exceptions
            if retryable_exceptions is not None
            else self.DEFAULT_RETRYABLE_EXCEPTIONS
        )

    def is_method_retryable(self, method: str) -> bool:
        return method.upper() in self.retryable_methods

    def is_status_retryable(self, status: int) -> bool:
        return status in self.retryable_statuses

    def is_exception_retryable(self, exc: BaseException) -> bool:
        from .exceptions import (
            StatusAssertionError,
            RequestValidationError,
            ResponseValidationError,
        )
        if isinstance(exc, (StatusAssertionError, RequestValidationError, ResponseValidationError)):
            return False

        return isinstance(exc, self.retryable_exceptions)

    def compute_delay(self, attempt: int, retry_after: Optional[float] = None) -> float:
        if retry_after is not None and retry_after >= 0:
            return min(retry_after, self.max_delay)

        base = self.base_delay * (2 ** (attempt - 1))
        jitter_value = random.uniform(0, self.jitter * base) if self.jitter else 0.0
        return min(base + jitter_value, self.max_delay)

    @staticmethod
    def parse_retry_after(value: Optional[str]) -> Optional[float]:
        if not value:
            return None
        try:
            return float(value)
        except ValueError:
            return None

# TODO: реализовать логику с RetryPolicy(Trivial)
