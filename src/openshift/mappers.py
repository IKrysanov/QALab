"""Преобразование Kubernetes SDK-моделей в стабильные доменные модели."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Optional

from .models import (
    ContainerStateInfo,
    ContainerStatusInfo,
    PodEventInfo,
    PodInfo,
)


def to_pod_info(pod: Any) -> PodInfo:
    """Преобразовать SDK pod без передачи SDK-моделей в тесты."""

    metadata = getattr(pod, "metadata", None)
    spec = getattr(pod, "spec", None)
    status = getattr(pod, "status", None)

    raw_labels = getattr(metadata, "labels", None) or {}
    labels = (
        {
            str(key): str(value)
            for key, value in raw_labels.items()
        }
        if isinstance(raw_labels, Mapping)
        else {}
    )
    conditions = getattr(status, "conditions", None) or []
    ready_condition = any(
        getattr(condition, "type", None) == "Ready"
        and str(getattr(condition, "status", "")).lower() == "true"
        for condition in conditions
    )
    phase = _optional_string(getattr(status, "phase", None))
    terminating = (
        getattr(metadata, "deletion_timestamp", None) is not None
    )
    normalized_container_statuses = tuple(
        _to_container_status_info(container_status)
        for container_status in (
            getattr(status, "container_statuses", None) or []
        )
        if getattr(container_status, "name", None) is not None
    )
    normalized_init_container_statuses = tuple(
        _to_container_status_info(container_status)
        for container_status in (
            getattr(status, "init_container_statuses", None) or []
        )
        if getattr(container_status, "name", None) is not None
    )
    controller_reference = next(
        (
            reference
            for reference in (
                getattr(metadata, "owner_references", None) or []
            )
            if getattr(reference, "controller", None) is True
        ),
        None,
    )
    containers = tuple(
        str(getattr(container, "name"))
        for container in (getattr(spec, "containers", None) or [])
        if getattr(container, "name", None) is not None
    )

    return PodInfo(
        name=str(getattr(metadata, "name", "")),
        namespace=str(getattr(metadata, "namespace", "")),
        uid=_optional_string(getattr(metadata, "uid", None)),
        phase=phase,
        ready=(
            phase == "Running"
            and ready_condition
            and not terminating
        ),
        terminating=terminating,
        labels=labels,
        containers=containers,
        container_statuses=normalized_container_statuses,
        init_container_statuses=normalized_init_container_statuses,
        restart_count=sum(
            container_status.restart_count
            for container_status in normalized_container_statuses
        ),
        pod_ip=_optional_string(getattr(status, "pod_ip", None)),
        node_name=_optional_string(getattr(spec, "node_name", None)),
        controller_kind=_optional_string(
            getattr(controller_reference, "kind", None)
        ),
        controller_name=_optional_string(
            getattr(controller_reference, "name", None)
        ),
        controller_uid=_optional_string(
            getattr(controller_reference, "uid", None)
        ),
        created_at=_optional_datetime(
            getattr(metadata, "creation_timestamp", None)
        ),
        started_at=_optional_datetime(
            getattr(status, "start_time", None)
        ),
        reason=_optional_string(getattr(status, "reason", None)),
        message=_optional_string(getattr(status, "message", None)),
    )


def to_pod_event_info(event: Any) -> PodEventInfo:
    """Преобразовать CoreV1 Event в стабильную диагностическую модель."""

    metadata = getattr(event, "metadata", None)
    source = getattr(event, "source", None)
    series = getattr(event, "series", None)
    count = _optional_int(getattr(event, "count", None))
    return PodEventInfo(
        event_type=_optional_string(getattr(event, "type", None)),
        reason=_optional_string(getattr(event, "reason", None)),
        message=_optional_string(getattr(event, "message", None)),
        count=count if count is not None else 1,
        source=(
            _optional_string(
                getattr(event, "reporting_component", None)
            )
            or _optional_string(getattr(source, "component", None))
        ),
        first_seen_at=(
            _optional_datetime(
                getattr(event, "first_timestamp", None)
            )
            or _optional_datetime(
                getattr(metadata, "creation_timestamp", None)
            )
        ),
        last_seen_at=(
            _optional_datetime(
                getattr(series, "last_observed_time", None)
            )
            or _optional_datetime(
                getattr(event, "last_timestamp", None)
            )
            or _optional_datetime(getattr(event, "event_time", None))
            or _optional_datetime(
                getattr(event, "first_timestamp", None)
            )
            or _optional_datetime(
                getattr(metadata, "creation_timestamp", None)
            )
        ),
    )


def _to_container_status_info(
        container_status: Any,
) -> ContainerStatusInfo:
    restart_count = _optional_int(
        getattr(container_status, "restart_count", None)
    )
    return ContainerStatusInfo(
        name=str(getattr(container_status, "name", "")),
        ready=getattr(container_status, "ready", None) is True,
        restart_count=restart_count if restart_count is not None else 0,
        image=_optional_string(
            getattr(container_status, "image", None)
        ),
        image_id=_optional_string(
            getattr(container_status, "image_id", None)
        ),
        state=_to_container_state_info(
            getattr(container_status, "state", None)
        ),
        last_state=_to_container_state_info(
            getattr(container_status, "last_state", None)
        ),
    )


def _to_container_state_info(
        state: Any,
) -> Optional[ContainerStateInfo]:
    if state is None:
        return None
    for state_name in ("waiting", "running", "terminated"):
        details = getattr(state, state_name, None)
        if details is None:
            continue
        return ContainerStateInfo(
            state=state_name,
            reason=_optional_string(getattr(details, "reason", None)),
            message=_optional_string(getattr(details, "message", None)),
            exit_code=_optional_int(
                getattr(details, "exit_code", None)
            ),
            signal=_optional_int(getattr(details, "signal", None)),
            started_at=_optional_datetime(
                getattr(details, "started_at", None)
            ),
            finished_at=_optional_datetime(
                getattr(details, "finished_at", None)
            ),
        )
    return None


def _optional_string(value: Any) -> Optional[str]:
    return str(value) if value is not None else None


def _optional_datetime(value: Any) -> Optional[datetime]:
    return value if isinstance(value, datetime) else None


def _optional_int(value: Any) -> Optional[int]:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None
