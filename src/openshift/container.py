"""Динамическая тестовая цель для команд внутри pod-контейнера."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Optional

from .exceptions import (
    OpenShiftCommandFailedError,
    OpenShiftContainerSelectionError,
    OpenShiftEnvironmentVariableNotFoundError,
)
from .models import CommandResult, PodEventInfo, PodInfo

if TYPE_CHECKING:
    from .client import OpenShiftClient


class OpenShiftContainer:
    """Разрешает актуальный pod по паттерну перед каждой операцией."""

    def __init__(
            self,
            client: "OpenShiftClient",
            name_pattern: str,
            *,
            container_name: Optional[str] = None,
            label_selector: Optional[str] = None,
            field_selector: Optional[str] = None,
    ) -> None:
        self._client = client
        self._name_pattern = name_pattern
        self._container_name = container_name
        self._label_selector = label_selector
        self._field_selector = field_selector

    @property
    def name_pattern(self) -> str:
        return self._name_pattern

    @property
    def configured_container_name(self) -> Optional[str]:
        return self._container_name

    def current_pod(self, *, ready_only: bool = True) -> PodInfo:
        """Получить единственный актуальный pod динамической цели."""

        if not isinstance(ready_only, bool):
            raise ValueError("ready_only must be bool")
        if ready_only:
            return self._client.wait_for_pod_by_pattern(
                self._name_pattern,
                label_selector=self._label_selector,
                field_selector=self._field_selector,
            )
        return self._client.find_pod(
            self._name_pattern,
            label_selector=self._label_selector,
            field_selector=self._field_selector,
            ready_only=False,
        )

    def pods(self, *, ready_only: bool = False) -> tuple[PodInfo, ...]:
        """Вернуть все pod цели, включая не-Ready для диагностики."""

        if not isinstance(ready_only, bool):
            raise ValueError("ready_only must be bool")
        return tuple(
            self._client.find_pods(
                self._name_pattern,
                label_selector=self._label_selector,
                field_selector=self._field_selector,
                ready_only=ready_only,
            )
        )

    def exec(
            self,
            command: Sequence[str],
            *,
            check: bool = True,
            timeout: Optional[float] = None,
            output_limit_bytes: Optional[int] = None,
    ) -> CommandResult:
        """Выполнить argv-команду в актуальном Ready pod."""

        pod = self.current_pod()
        container_name = self._resolve_container_name(pod)
        return self._client.exec_command(
            pod.name,
            command,
            container=container_name,
            check=check,
            timeout=timeout,
            output_limit_bytes=output_limit_bytes,
        )

    def sh(
            self,
            script: str,
            *,
            shell: str = "/bin/sh",
            check: bool = True,
            timeout: Optional[float] = None,
            output_limit_bytes: Optional[int] = None,
    ) -> CommandResult:
        """Выполнить shell-фрагмент; подходит для pipe и redirect."""

        if not isinstance(script, str) or not script.strip():
            raise ValueError("script must not be empty")
        if not isinstance(shell, str) or not shell.strip():
            raise ValueError("shell must not be empty")
        return self.exec(
            (shell, "-c", script),
            check=check,
            timeout=timeout,
            output_limit_bytes=output_limit_bytes,
        )

    def logs(
            self,
            *,
            pod_name: Optional[str] = None,
            ready_only: bool = True,
            previous: bool = False,
            tail_lines: int = 500,
            limit_bytes: Optional[int] = None,
            since_seconds: Optional[int] = None,
            timestamps: bool = True,
    ) -> str:
        """Прочитать хвост логов текущего либо явно указанного pod."""

        if pod_name is not None and (
                not isinstance(pod_name, str)
                or not pod_name.strip()
        ):
            raise ValueError("pod_name must not be empty")
        if not isinstance(ready_only, bool):
            raise ValueError("ready_only must be bool")

        pod = (
            self._client.get_pod(pod_name)
            if pod_name is not None
            else self.current_pod(ready_only=ready_only)
        )
        container_name = self._resolve_container_name(pod)
        return self._client.read_pod_logs(
            pod.name,
            container=container_name,
            previous=previous,
            tail_lines=tail_lines,
            limit_bytes=limit_bytes,
            since_seconds=since_seconds,
            timestamps=timestamps,
        )

    def events(
            self,
            *,
            pod_name: Optional[str] = None,
            ready_only: bool = True,
    ) -> tuple[PodEventInfo, ...]:
        """Вернуть события текущего либо явно указанного pod."""

        if pod_name is not None and (
                not isinstance(pod_name, str)
                or not pod_name.strip()
        ):
            raise ValueError("pod_name must not be empty")
        if not isinstance(ready_only, bool):
            raise ValueError("ready_only must be bool")

        pod = (
            self._client.get_pod(pod_name)
            if pod_name is not None
            else self.current_pod(ready_only=ready_only)
        )
        return tuple(
            self._client.list_pod_events(
                pod.name,
                pod_uid=pod.uid,
            )
        )

    def get_env(
            self,
            name: str,
            *,
            required: bool = True,
            timeout: Optional[float] = None,
            output_limit_bytes: Optional[int] = None,
    ) -> Optional[str]:
        """Прочитать одну env-переменную без shell-интерполяции."""

        if (
                not isinstance(name, str)
                or not name
                or "=" in name
                or "\x00" in name
        ):
            raise ValueError(
                "environment variable name must be a non-empty string "
                "without '=' or NUL"
            )
        if not isinstance(required, bool):
            raise ValueError("required must be bool")

        result = self.exec(
            ("printenv", name),
            check=False,
            timeout=timeout,
            output_limit_bytes=output_limit_bytes,
        )
        if result.exit_code == 0:
            return (
                result.stdout[:-1]
                if result.stdout.endswith("\n")
                else result.stdout
            )
        if result.exit_code == 1:
            if not required:
                return None
            raise OpenShiftEnvironmentVariableNotFoundError(
                result.namespace,
                result.pod_name,
                result.container_name,
                name,
            )
        raise OpenShiftCommandFailedError(result)

    def _resolve_container_name(self, pod: PodInfo) -> str:
        if self._container_name is not None:
            if self._container_name in pod.containers:
                return self._container_name
        elif len(pod.containers) == 1:
            return pod.containers[0]

        raise OpenShiftContainerSelectionError(
            pod.namespace,
            pod.name,
            self._container_name,
            pod.containers,
        )
