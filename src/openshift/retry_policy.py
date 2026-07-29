"""Классификация ошибок polling-операций OpenShift."""

from __future__ import annotations

import ssl
from dataclasses import dataclass
from typing import Any

_RETRYABLE_API_STATUSES = frozenset({429, 500, 502, 503, 504})
_RETRYABLE_CAUSE_TYPES = frozenset({
    "ConnectTimeoutError",
    "ConnectionError",
    "MaxRetryError",
    "ProtocolError",
    "ReadTimeoutError",
    "TimeoutError",
})
_CERTIFICATE_ERROR_TYPES = frozenset({
    "CertificateError",
    "SSLCertVerificationError",
})
_CERTIFICATE_ERROR_MARKERS = (
    "certificate verify failed",
    "certificate_verify_failed",
    "certificate has expired",
    "certificate is not yet valid",
    "hostname mismatch",
    "self-signed certificate",
    "unable to get local issuer certificate",
    "unable to verify the first certificate",
)


@dataclass(frozen=True)
class RetryDecision:
    """Результат классификации ошибки ожидания."""

    retry: bool
    reason: str


def classify_wait_error(exc: Exception) -> RetryDecision:
    """Определить, можно ли безопасно повторить polling API-вызов."""

    if _is_certificate_validation_error(exc):
        return RetryDecision(
            retry=False,
            reason="tls_certificate_validation",
        )

    status = getattr(exc, "status", None)
    if status in _RETRYABLE_API_STATUSES:
        return RetryDecision(
            retry=True,
            reason="retryable_http_status",
        )

    cause_type = (
        getattr(exc, "cause_type", None)
        or type(exc).__name__
    )
    if status is None and cause_type in _RETRYABLE_CAUSE_TYPES:
        return RetryDecision(
            retry=True,
            reason="retryable_transport_error",
        )

    return RetryDecision(
        retry=False,
        reason="non_retryable_error",
    )


def _is_certificate_validation_error(exc: Exception) -> bool:
    """Найти ошибку сертификата даже под обёртками SDK/urllib3."""

    pending: list[Any] = [exc]
    visited: set[int] = set()

    while pending:
        current = pending.pop()
        current_id = id(current)
        if current_id in visited:
            continue
        visited.add(current_id)

        if isinstance(
                current,
                (ssl.CertificateError, ssl.SSLCertVerificationError),
        ):
            return True
        if type(current).__name__ in _CERTIFICATE_ERROR_TYPES:
            return True

        normalized_message = str(current).casefold()
        if any(
                marker in normalized_message
                for marker in _CERTIFICATE_ERROR_MARKERS
        ):
            return True

        if not isinstance(current, BaseException):
            continue

        pending.extend(
            nested
            for nested in (
                current.__cause__,
                current.__context__,
                getattr(current, "reason", None),
                *current.args,
            )
            if isinstance(nested, (BaseException, str))
        )

    return False
