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
    OpenShiftOperationError,
    OpenShiftPodSelectionError,
    OpenShiftWaitTimeoutError,
)
from .models import CommandResult, PodInfo, PodRestartResult
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
    "OpenShiftOperationError",
    "OpenShiftPodSelectionError",
    "OpenShiftServiceFactory",
    "OpenShiftWaitTimeoutError",
    "PodExecutor",
    "PodInfo",
    "PodRestartResult",
]
