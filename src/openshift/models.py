"""Типизированные модели OpenShift-клиента."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping, Optional


@dataclass(frozen=True)
class ContainerStateInfo:
    """Текущее или предыдущее состояние одного контейнера."""

    state: str
    reason: Optional[str] = None
    message: Optional[str] = None
    exit_code: Optional[int] = None
    signal: Optional[int] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


@dataclass(frozen=True)
class ContainerStatusInfo:
    """Диагностическое состояние контейнера без SDK-моделей."""

    name: str
    ready: bool
    restart_count: int
    image: Optional[str] = None
    image_id: Optional[str] = None
    state: Optional[ContainerStateInfo] = None
    last_state: Optional[ContainerStateInfo] = None


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
    container_statuses: tuple[ContainerStatusInfo, ...] = ()
    init_container_statuses: tuple[ContainerStatusInfo, ...] = ()
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
class PodEventInfo:
    """Событие Kubernetes, относящееся к конкретному pod."""

    event_type: Optional[str]
    reason: Optional[str]
    message: Optional[str]
    count: int
    source: Optional[str] = None
    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None


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
