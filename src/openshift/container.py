"""Динамическая тестовая цель для команд внутри pod-контейнера."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Optional

from .exceptions import OpenShiftContainerSelectionError
from .models import CommandResult, PodInfo

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

    def current_pod(self) -> PodInfo:
        """Получить единственный актуальный Ready pod."""

        return self._client.find_pod(
            self._name_pattern,
            label_selector=self._label_selector,
            field_selector=self._field_selector,
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
            previous: bool = False,
            tail_lines: int = 500,
            limit_bytes: Optional[int] = None,
            timestamps: bool = True,
    ) -> str:
        """Прочитать ограниченный хвост логов актуального контейнера."""

        pod = self.current_pod()
        container_name = self._resolve_container_name(pod)
        return self._client.read_pod_logs(
            pod.name,
            container=container_name,
            previous=previous,
            tail_lines=tail_lines,
            limit_bytes=limit_bytes,
            timestamps=timestamps,
        )

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
