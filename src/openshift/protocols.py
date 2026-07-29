"""Узкие интерфейсы зависимостей OpenShift-клиента."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

from .config import OpenShiftConfig
from .models import CommandResult


class CoreV1Service(Protocol):
    """Используемая клиентом часть Kubernetes ``CoreV1Api``."""

    def list_namespaced_pod(
            self,
            namespace: str,
            **kwargs: Any,
    ) -> Any:
        ...

    def read_namespaced_pod(
            self,
            name: str,
            namespace: str,
            **kwargs: Any,
    ) -> Any:
        ...

    def delete_namespaced_pod(
            self,
            name: str,
            namespace: str,
            **kwargs: Any,
    ) -> Any:
        ...

    def read_namespaced_pod_log(
            self,
            name: str,
            namespace: str,
            **kwargs: Any,
    ) -> str:
        ...

    def list_namespaced_event(
            self,
            namespace: str,
            **kwargs: Any,
    ) -> Any:
        ...

    def connect_post_namespaced_pod_exec(
            self,
            name: str,
            namespace: str,
            **kwargs: Any,
    ) -> Any:
        ...


class KubernetesApiClient(Protocol):
    """Жизненный цикл низкоуровневого Kubernetes API client."""

    def close(self) -> None:
        ...


class OpenShiftServiceFactory(Protocol):
    """Фабрика Kubernetes API, отделённая от операций с pod."""

    def create(
            self,
            config: OpenShiftConfig,
    ) -> tuple[CoreV1Service, KubernetesApiClient]:
        ...


class PodExecutor(Protocol):
    """Транспорт выполнения команд через Kubernetes exec WebSocket."""

    def execute(
            self,
            namespace: str,
            pod_name: str,
            container_name: str,
            command: Sequence[str],
            *,
            timeout: float,
            output_limit_bytes: int,
    ) -> CommandResult:
        ...


class Clock(Protocol):
    """Источник времени, подменяемый в тестах polling-логики."""

    def monotonic(self) -> float:
        ...

    def sleep(self, seconds: float) -> None:
        ...
