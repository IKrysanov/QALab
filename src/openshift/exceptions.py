"""Доменные исключения OpenShift-клиента."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .models import CommandResult


class OpenShiftClientError(RuntimeError):
    """Базовая ошибка OpenShift-клиента."""


class OpenShiftConfigurationError(OpenShiftClientError, ValueError):
    """Конфигурация Kubernetes API отсутствует или противоречива."""


class OpenShiftDependencyError(OpenShiftClientError, ImportError):
    """Не установлена библиотека, необходимая клиенту."""


class OpenShiftClientClosedError(OpenShiftClientError):
    """Операция вызвана после закрытия клиента."""


class OpenShiftOperationError(OpenShiftClientError):
    """Ошибка Kubernetes API с безопасным диагностическим контекстом."""

    def __init__(
            self,
            operation: str,
            namespace: str,
            resource: str,
            *,
            resource_name: Optional[str] = None,
            cause_type: Optional[str] = None,
            status: Optional[int] = None,
            reason: Optional[str] = None,
            request_id: Optional[str] = None,
    ) -> None:
        self.operation = operation
        self.namespace = namespace
        self.resource = resource
        self.resource_name = resource_name
        self.cause_type = cause_type
        self.status = status
        self.reason = reason
        self.request_id = request_id

        target = f"{resource} namespace={namespace!r}"
        if resource_name is not None:
            target = f"{target} name={resource_name!r}"

        details = [
            f"operation={operation!r}",
            f"target={target!r}",
        ]
        if cause_type is not None:
            details.append(f"cause_type={cause_type!r}")
        if status is not None:
            details.append(f"status={status}")
        if reason is not None:
            details.append(f"reason={reason!r}")
        if request_id is not None:
            details.append(f"request_id={request_id!r}")
        super().__init__(
            f"OpenShift operation failed: {', '.join(details)}"
        )


class OpenShiftPodSelectionError(OpenShiftClientError):
    """Name pattern не выбрал ровно один подходящий pod."""

    def __init__(
            self,
            namespace: str,
            name_pattern: str,
            matches: tuple[str, ...],
            *,
            ready_only: bool,
    ) -> None:
        self.namespace = namespace
        self.name_pattern = name_pattern
        self.matches = matches
        self.ready_only = ready_only

        super().__init__(
            "OpenShift pod selection failed: "
            f"namespace={namespace!r}, name_pattern={name_pattern!r}, "
            f"ready_only={ready_only}, matches={matches!r}"
        )


class OpenShiftContainerSelectionError(OpenShiftClientError):
    """В pod невозможно однозначно выбрать контейнер."""

    def __init__(
            self,
            namespace: str,
            pod_name: str,
            requested_container: Optional[str],
            available_containers: tuple[str, ...],
    ) -> None:
        self.namespace = namespace
        self.pod_name = pod_name
        self.requested_container = requested_container
        self.available_containers = available_containers

        super().__init__(
            "OpenShift container selection failed: "
            f"namespace={namespace!r}, pod_name={pod_name!r}, "
            f"requested_container={requested_container!r}, "
            f"available_containers={available_containers!r}"
        )


class OpenShiftCommandFailedError(OpenShiftClientError):
    """Процесс в контейнере завершился с ненулевым кодом."""

    def __init__(self, result: "CommandResult") -> None:
        self.result = result
        output = result.stderr or result.stdout
        output_excerpt = output[-2_000:]
        super().__init__(
            "OpenShift command failed: "
            f"namespace={result.namespace!r}, "
            f"pod_name={result.pod_name!r}, "
            f"container_name={result.container_name!r}, "
            f"executable={result.command[0]!r}, "
            f"exit_code={result.exit_code}, "
            f"output_excerpt={output_excerpt!r}"
        )


class OpenShiftCommandTimeoutError(OpenShiftClientError, TimeoutError):
    """Команда в контейнере не завершилась до timeout."""

    def __init__(
            self,
            namespace: str,
            pod_name: str,
            container_name: str,
            executable: str,
            timeout: float,
    ) -> None:
        self.namespace = namespace
        self.pod_name = pod_name
        self.container_name = container_name
        self.executable = executable
        self.timeout = timeout
        super().__init__(
            "OpenShift command timed out: "
            f"namespace={namespace!r}, pod_name={pod_name!r}, "
            f"container_name={container_name!r}, "
            f"executable={executable!r}, timeout={timeout}"
        )


class OpenShiftCommandOutputTooLargeError(OpenShiftClientError):
    """Вывод команды превысил безопасный лимит памяти."""

    def __init__(
            self,
            namespace: str,
            pod_name: str,
            container_name: str,
            executable: str,
            limit_bytes: int,
    ) -> None:
        self.namespace = namespace
        self.pod_name = pod_name
        self.container_name = container_name
        self.executable = executable
        self.limit_bytes = limit_bytes
        super().__init__(
            "OpenShift command output exceeded limit: "
            f"namespace={namespace!r}, pod_name={pod_name!r}, "
            f"container_name={container_name!r}, "
            f"executable={executable!r}, limit_bytes={limit_bytes}"
        )


class OpenShiftWaitTimeoutError(OpenShiftClientError, TimeoutError):
    """Ожидаемое состояние ресурса не достигнуто за отведённое время."""

    def __init__(
            self,
            operation: str,
            namespace: str,
            timeout: float,
            *,
            last_observed: Optional[str] = None,
    ) -> None:
        self.operation = operation
        self.namespace = namespace
        self.timeout = timeout
        self.last_observed = last_observed

        message = (
            "OpenShift wait timed out: "
            f"operation={operation!r}, namespace={namespace!r}, "
            f"timeout={timeout}"
        )
        if last_observed is not None:
            message = f"{message}, last_observed={last_observed!r}"
        super().__init__(message)
