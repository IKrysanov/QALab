"""Конфигурация подключения к OpenShift через Kubernetes API."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from .exceptions import OpenShiftConfigurationError

_AUTH_MODES = frozenset({"auto", "in_cluster", "kubeconfig"})


@dataclass(frozen=True)
class OpenShiftConfig:
    """Настройки Kubernetes API и детерминированных ожиданий в тестах."""

    namespace: str
    auth_mode: str = "auto"
    kubeconfig_path: Optional[str] = None
    context: Optional[str] = None
    verify_ssl: Optional[bool] = None
    ssl_ca_cert: Optional[str] = None
    connect_timeout: float = 5.0
    read_timeout: float = 30.0
    wait_timeout: float = 300.0
    poll_interval: float = 2.0
    log_limit_bytes: int = 1_000_000
    exec_timeout: float = 60.0
    exec_output_limit_bytes: int = 1_000_000

    def __post_init__(self) -> None:
        if not isinstance(self.namespace, str):
            raise OpenShiftConfigurationError(
                "namespace must be a string"
            )
        normalized_namespace = self.namespace.strip()
        if not normalized_namespace:
            raise OpenShiftConfigurationError(
                "namespace must not be empty"
            )
        object.__setattr__(self, "namespace", normalized_namespace)

        if not isinstance(self.auth_mode, str):
            raise OpenShiftConfigurationError(
                "auth_mode must be a string"
            )
        normalized_mode = self.auth_mode.strip().lower()
        if normalized_mode not in _AUTH_MODES:
            raise OpenShiftConfigurationError(
                "auth_mode must be one of: auto, in_cluster, kubeconfig"
            )
        object.__setattr__(self, "auth_mode", normalized_mode)

        for attribute in ("kubeconfig_path", "context", "ssl_ca_cert"):
            value = getattr(self, attribute)
            if value is None:
                continue
            if not isinstance(value, str):
                raise OpenShiftConfigurationError(
                    f"{attribute} must be a string"
                )
            normalized_value = value.strip()
            if not normalized_value:
                raise OpenShiftConfigurationError(
                    f"{attribute} must not be empty"
                )
            object.__setattr__(self, attribute, normalized_value)

        if self.verify_ssl is not None and not isinstance(
                self.verify_ssl,
                bool,
        ):
            raise OpenShiftConfigurationError(
                "verify_ssl must be bool or None"
            )
        if normalized_mode == "in_cluster" and (
                self.kubeconfig_path is not None
                or self.context is not None
        ):
            raise OpenShiftConfigurationError(
                "kubeconfig_path/context cannot be used with in_cluster auth"
            )
        if self.verify_ssl is False and self.ssl_ca_cert is not None:
            raise OpenShiftConfigurationError(
                "ssl_ca_cert cannot be used when verify_ssl is false"
            )

        for attribute in (
                "connect_timeout",
                "read_timeout",
                "wait_timeout",
                "poll_interval",
                "exec_timeout",
        ):
            value = getattr(self, attribute)
            if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(value)
                    or value <= 0
            ):
                raise OpenShiftConfigurationError(
                    f"{attribute} must be greater than zero"
                )

        if (
                isinstance(self.log_limit_bytes, bool)
                or not isinstance(self.log_limit_bytes, int)
                or self.log_limit_bytes < 1
        ):
            raise OpenShiftConfigurationError(
                "log_limit_bytes must be greater than zero"
            )
        if (
                isinstance(self.exec_output_limit_bytes, bool)
                or not isinstance(self.exec_output_limit_bytes, int)
                or self.exec_output_limit_bytes < 1
        ):
            raise OpenShiftConfigurationError(
                "exec_output_limit_bytes must be greater than zero"
            )

    @property
    def request_timeout(self) -> tuple[float, float]:
        """Таймауты соединения и чтения для вызовов Kubernetes SDK."""

        return self.connect_timeout, self.read_timeout
