"""Типизированные модели OpenShift-клиента."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping, Optional


@dataclass(frozen=True)
class PodInfo:
    """Стабильное представление pod без зависимости от SDK-моделей."""

    name: str
    namespace: str
    uid: Optional[str]
    phase: Optional[str]
    ready: bool
    terminating: bool
    labels: Mapping[str, str] = field(default_factory=dict)
    containers: tuple[str, ...] = ()
    restart_count: int = 0
    pod_ip: Optional[str] = None
    node_name: Optional[str] = None
    controller_kind: Optional[str] = None
    controller_name: Optional[str] = None
    controller_uid: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    reason: Optional[str] = None
    message: Optional[str] = None


@dataclass(frozen=True)
class PodRestartResult:
    """Pod до удаления и Ready-замена, созданная его контроллером."""

    previous: PodInfo
    replacement: PodInfo


@dataclass(frozen=True)
class CommandResult:
    """Результат неинтерактивной команды внутри контейнера."""

    namespace: str
    pod_name: str
    container_name: str
    command: tuple[str, ...]
    stdout: str
    stderr: str
    exit_code: int
    duration_seconds: float

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0
