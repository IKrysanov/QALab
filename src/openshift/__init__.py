"""Тестовый OpenShift-клиент поверх официального Kubernetes SDK."""

from .client import OpenShiftClient
from .config import OpenShiftConfig
from .container import OpenShiftContainer
from .exceptions import (
    OpenShiftClientClosedError,
    OpenShiftClientError,
    OpenShiftCommandFailedError,
    OpenShiftCommandOutputTooLargeError,
    OpenShiftCommandTimeoutError,
    OpenShiftConfigurationError,
    OpenShiftContainerSelectionError,
    OpenShiftDependencyError,
    OpenShiftEnvironmentVariableNotFoundError,
    OpenShiftOperationError,
    OpenShiftPodSelectionError,
    OpenShiftWaitTimeoutError,
)
from .models import (
    CommandResult,
    ContainerStateInfo,
    ContainerStatusInfo,
    PodEventInfo,
    PodInfo,
    PodRestartResult,
)
from .protocols import (
    Clock,
    CoreV1Service,
    KubernetesApiClient,
    OpenShiftServiceFactory,
    PodExecutor,
)

__all__ = [
    "Clock",
    "CommandResult",
    "ContainerStateInfo",
    "ContainerStatusInfo",
    "CoreV1Service",
    "KubernetesApiClient",
    "OpenShiftClient",
    "OpenShiftClientClosedError",
    "OpenShiftClientError",
    "OpenShiftCommandFailedError",
    "OpenShiftCommandOutputTooLargeError",
    "OpenShiftCommandTimeoutError",
    "OpenShiftConfig",
    "OpenShiftConfigurationError",
    "OpenShiftContainer",
    "OpenShiftContainerSelectionError",
    "OpenShiftDependencyError",
    "OpenShiftEnvironmentVariableNotFoundError",
    "OpenShiftOperationError",
    "OpenShiftPodSelectionError",
    "OpenShiftServiceFactory",
    "OpenShiftWaitTimeoutError",
    "PodExecutor",
    "PodEventInfo",
    "PodInfo",
    "PodRestartResult",
]
