"""Высокоуровневые операции с pod в OpenShift."""

from __future__ import annotations

import logging
import math
import time
from collections.abc import Sequence, Set as AbstractSet
from fnmatch import fnmatchcase
from threading import RLock
from types import TracebackType
from typing import Any, Mapping, NoReturn, Optional

from utils.logger import get_logger, log_event

from .config import OpenShiftConfig
from .container import OpenShiftContainer
from .executor import (
    KubernetesPodExecutor,
    PodExecTransportOutputTooLargeError,
    PodExecTransportTimeoutError,
)
from .exceptions import (
    OpenShiftClientClosedError,
    OpenShiftCommandFailedError,
    OpenShiftCommandOutputTooLargeError,
    OpenShiftCommandTimeoutError,
    OpenShiftOperationError,
    OpenShiftPodSelectionError,
    OpenShiftWaitTimeoutError,
)
from .kubernetes_factory import KubernetesOpenShiftServiceFactory
from .mappers import to_pod_event_info, to_pod_info
from .models import CommandResult, PodEventInfo, PodInfo, PodRestartResult
from .protocols import (
    Clock,
    CoreV1Service,
    KubernetesApiClient,
    OpenShiftServiceFactory,
    PodExecutor,
)
from .retry_policy import classify_wait_error

logger = get_logger("openshift.client")


class SystemClock:
    """Системный источник времени для polling."""

    def monotonic(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


class OpenShiftClient:
    """Лёгкий тестовый клиент pod-операций поверх Kubernetes API."""

    def __init__(
            self,
            config: OpenShiftConfig,
            *,
            core_api: Optional[CoreV1Service] = None,
            api_client: Optional[KubernetesApiClient] = None,
            service_factory: Optional[OpenShiftServiceFactory] = None,
            pod_executor: Optional[PodExecutor] = None,
            clock: Optional[Clock] = None,
    ) -> None:
        if core_api is not None and service_factory is not None:
            raise ValueError("Pass either core_api or service_factory, not both")
        if core_api is None and api_client is not None:
            raise ValueError("api_client requires an injected core_api")

        self._config = config
        if core_api is None:
            factory = (
                service_factory
                or KubernetesOpenShiftServiceFactory()
            )
            self._core_api, self._api_client = factory.create(config)
            self._owns_api_client = True
        else:
            self._core_api = core_api
            self._api_client = api_client
            self._owns_api_client = False
        self._pod_executor = (
            pod_executor
            if pod_executor is not None
            else KubernetesPodExecutor(self._core_api)
        )
        self._clock = clock or SystemClock()
        self._api_lock = RLock()
        self._closed = False

    @property
    def namespace(self) -> str:
        return self._config.namespace

    @property
    def closed(self) -> bool:
        return self._closed

    def __enter__(self) -> "OpenShiftClient":
        self._ensure_open()
        return self

    def __exit__(
            self,
            exc_type: Optional[type[BaseException]],
            exc: Optional[BaseException],
            traceback: Optional[TracebackType],
    ) -> None:
        try:
            self.close()
        except OpenShiftOperationError:
            if exc_type is None:
                raise
            log_event(
                logger,
                logging.ERROR,
                "openshift_client_close_error_suppressed",
                namespace=self.namespace,
                original_exception=exc_type.__name__,
            )

    def close(self) -> None:
        """Идемпотентно закрыть принадлежащий клиенту Kubernetes transport."""

        if self._closed:
            return

        try:
            with self._api_lock:
                if self._owns_api_client and self._api_client is not None:
                    self._api_client.close()
        except Exception as exc:
            self._raise_operation_error(
                "close",
                "api_client",
                None,
                exc,
            )
        finally:
            self._closed = True

        log_event(
            logger,
            logging.INFO,
            "openshift_client_closed",
            namespace=self.namespace,
            owns_api_client=self._owns_api_client,
        )

    def list_pods(
            self,
            *,
            label_selector: Optional[str] = None,
            field_selector: Optional[str] = None,
    ) -> list[PodInfo]:
        """Вернуть pod текущего namespace с опциональными selectors."""

        self._ensure_open()
        self._validate_optional_text("label_selector", label_selector)
        self._validate_optional_text("field_selector", field_selector)

        request: dict[str, Any] = {
            "_request_timeout": self._config.request_timeout,
        }
        if label_selector is not None:
            request["label_selector"] = label_selector
        if field_selector is not None:
            request["field_selector"] = field_selector

        try:
            with self._api_lock:
                response = self._core_api.list_namespaced_pod(
                    self.namespace,
                    **request,
                )
        except Exception as exc:
            self._raise_operation_error(
                "list_namespaced_pod",
                "pods",
                label_selector,
                exc,
            )

        return [
            to_pod_info(pod)
            for pod in (getattr(response, "items", None) or [])
        ]

    def find_pods(
            self,
            name_pattern: str,
            *,
            label_selector: Optional[str] = None,
            field_selector: Optional[str] = None,
            ready_only: bool = False,
    ) -> list[PodInfo]:
        """Найти pod по case-sensitive glob имени внутри namespace."""

        self._ensure_open()
        self._validate_required_text("name_pattern", name_pattern)
        self._validate_bool("ready_only", ready_only)

        pods = self.list_pods(
            label_selector=label_selector,
            field_selector=field_selector,
        )
        return sorted(
            (
                pod
                for pod in pods
                if fnmatchcase(pod.name, name_pattern)
                and (pod.ready or not ready_only)
            ),
            key=lambda pod: pod.name,
        )

    def find_pod(
            self,
            name_pattern: str,
            *,
            label_selector: Optional[str] = None,
            field_selector: Optional[str] = None,
            ready_only: bool = True,
    ) -> PodInfo:
        """Вернуть единственный pod по glob или завершиться неоднозначностью."""

        matches = self.find_pods(
            name_pattern,
            label_selector=label_selector,
            field_selector=field_selector,
            ready_only=ready_only,
        )
        selected = self._select_single_pod(
            matches,
            name_pattern=name_pattern,
            ready_only=ready_only,
        )
        log_event(
            logger,
            logging.INFO,
            "openshift_pod_selected",
            namespace=self.namespace,
            name_pattern=name_pattern,
            label_selector=label_selector,
            pod=selected.name,
            uid=selected.uid,
            ready=selected.ready,
        )
        return selected

    def wait_for_pod_by_pattern(
            self,
            name_pattern: str,
            *,
            label_selector: Optional[str] = None,
            field_selector: Optional[str] = None,
            timeout: Optional[float] = None,
            poll_interval: Optional[float] = None,
    ) -> PodInfo:
        """Дождаться единственного Ready pod по glob-паттерну."""

        self._ensure_open()
        self._validate_required_text("name_pattern", name_pattern)
        self._validate_optional_text(
            "label_selector",
            label_selector,
        )
        self._validate_optional_text(
            "field_selector",
            field_selector,
        )
        effective_timeout, effective_interval = self._wait_settings(
            timeout,
            poll_interval,
        )
        deadline = self._clock.monotonic() + effective_timeout
        last_observed = "no pods"

        while True:
            try:
                matches = self.find_pods(
                    name_pattern,
                    label_selector=label_selector,
                    field_selector=field_selector,
                )
                ready_matches = [pod for pod in matches if pod.ready]
                if len(ready_matches) == 1:
                    selected = ready_matches[0]
                    log_event(
                        logger,
                        logging.INFO,
                        "openshift_pod_selected",
                        namespace=self.namespace,
                        name_pattern=name_pattern,
                        label_selector=label_selector,
                        pod=selected.name,
                        uid=selected.uid,
                        ready=True,
                        waited=True,
                    )
                    return selected
                last_observed = self._pods_summary(matches)
            except OpenShiftOperationError as exc:
                if not self._is_retryable_wait_error(
                        "wait_for_pod_by_pattern",
                        exc,
                ):
                    raise
                last_observed = self._wait_error_summary(exc)

            if not self._sleep_until_next_poll(
                    deadline,
                    effective_interval,
            ):
                raise OpenShiftWaitTimeoutError(
                    f"wait_for_pod_by_pattern:{name_pattern}",
                    self.namespace,
                    effective_timeout,
                    last_observed=last_observed,
                )

    def container(
            self,
            name_pattern: str,
            *,
            container_name: Optional[str] = None,
            label_selector: Optional[str] = None,
            field_selector: Optional[str] = None,
    ) -> OpenShiftContainer:
        """Создать динамическую цель контейнера для pytest fixture."""

        self._ensure_open()
        self._validate_required_text("name_pattern", name_pattern)
        self._validate_optional_text(
            "container_name",
            container_name,
        )
        self._validate_optional_text(
            "label_selector",
            label_selector,
        )
        self._validate_optional_text(
            "field_selector",
            field_selector,
        )
        return OpenShiftContainer(
            self,
            name_pattern,
            container_name=container_name,
            label_selector=label_selector,
            field_selector=field_selector,
        )

    def exec_command(
            self,
            pod_name: str,
            command: Sequence[str],
            *,
            container: str,
            check: bool = False,
            timeout: Optional[float] = None,
            output_limit_bytes: Optional[int] = None,
    ) -> CommandResult:
        """Выполнить неинтерактивную argv-команду внутри контейнера."""

        self._ensure_open()
        self._validate_required_text("pod_name", pod_name)
        self._validate_required_text("container", container)
        normalized_command = self._validate_command(command)
        self._validate_bool("check", check)
        effective_timeout = (
            self._config.exec_timeout
            if timeout is None
            else timeout
        )
        effective_output_limit = (
            self._config.exec_output_limit_bytes
            if output_limit_bytes is None
            else output_limit_bytes
        )
        self._validate_positive_number("timeout", effective_timeout)
        self._validate_positive_int(
            "output_limit_bytes",
            effective_output_limit,
        )

        log_event(
            logger,
            logging.INFO,
            "openshift_command_started",
            namespace=self.namespace,
            pod=pod_name,
            container=container,
            executable=normalized_command[0],
            argument_count=len(normalized_command) - 1,
            timeout=float(effective_timeout),
            output_limit_bytes=effective_output_limit,
        )
        try:
            with self._api_lock:
                result = self._pod_executor.execute(
                    self.namespace,
                    pod_name,
                    container,
                    normalized_command,
                    timeout=float(effective_timeout),
                    output_limit_bytes=effective_output_limit,
                )
            if not isinstance(result, CommandResult):
                raise TypeError(
                    "PodExecutor.execute must return CommandResult"
                )
        except PodExecTransportTimeoutError as exc:
            log_event(
                logger,
                logging.WARNING,
                "openshift_command_timed_out",
                namespace=self.namespace,
                pod=pod_name,
                container=container,
                executable=normalized_command[0],
                timeout=float(effective_timeout),
            )
            raise OpenShiftCommandTimeoutError(
                self.namespace,
                pod_name,
                container,
                normalized_command[0],
                float(effective_timeout),
            ) from exc
        except PodExecTransportOutputTooLargeError as exc:
            log_event(
                logger,
                logging.WARNING,
                "openshift_command_output_too_large",
                namespace=self.namespace,
                pod=pod_name,
                container=container,
                executable=normalized_command[0],
                output_limit_bytes=effective_output_limit,
            )
            raise OpenShiftCommandOutputTooLargeError(
                self.namespace,
                pod_name,
                container,
                normalized_command[0],
                effective_output_limit,
            ) from exc
        except Exception as exc:
            self._raise_operation_error(
                "connect_post_namespaced_pod_exec",
                "pod",
                pod_name,
                exc,
            )

        log_level = logging.INFO if result.succeeded else logging.WARNING
        log_event(
            logger,
            log_level,
            "openshift_command_completed",
            namespace=self.namespace,
            pod=pod_name,
            container=container,
            executable=normalized_command[0],
            argument_count=len(normalized_command) - 1,
            exit_code=result.exit_code,
            duration_seconds=round(result.duration_seconds, 6),
            stdout_bytes=len(result.stdout.encode("utf-8")),
            stderr_bytes=len(result.stderr.encode("utf-8")),
        )
        if check and not result.succeeded:
            raise OpenShiftCommandFailedError(result)
        return result

    def get_pod(self, pod_name: str) -> PodInfo:
        """Получить текущее состояние pod."""

        self._ensure_open()
        self._validate_required_text("pod_name", pod_name)
        try:
            pod = self._read_pod(pod_name)
        except Exception as exc:
            self._raise_operation_error(
                "read_namespaced_pod",
                "pod",
                pod_name,
                exc,
            )
        return to_pod_info(pod)

    def pod_exists(self, pod_name: str) -> bool:
        """Проверить существование pod, не скрывая ошибки RBAC."""

        self._ensure_open()
        self._validate_required_text("pod_name", pod_name)
        try:
            self._read_pod(pod_name)
            return True
        except Exception as exc:
            if self._is_not_found(exc):
                return False
            self._raise_operation_error(
                "read_namespaced_pod",
                "pod",
                pod_name,
                exc,
            )

    def read_pod_logs(
            self,
            pod_name: str,
            *,
            container: Optional[str] = None,
            previous: bool = False,
            tail_lines: int = 500,
            limit_bytes: Optional[int] = None,
            since_seconds: Optional[int] = None,
            timestamps: bool = True,
    ) -> str:
        """Прочитать ограниченный хвост логов pod для диагностики теста."""

        self._ensure_open()
        self._validate_required_text("pod_name", pod_name)
        self._validate_optional_text("container", container)
        self._validate_positive_int("tail_lines", tail_lines)
        if since_seconds is not None:
            self._validate_positive_int("since_seconds", since_seconds)
        self._validate_bool("previous", previous)
        self._validate_bool("timestamps", timestamps)
        effective_limit = (
            self._config.log_limit_bytes
            if limit_bytes is None
            else limit_bytes
        )
        self._validate_positive_int("limit_bytes", effective_limit)

        request: dict[str, Any] = {
            "previous": previous,
            "tail_lines": tail_lines,
            "limit_bytes": effective_limit,
            "timestamps": timestamps,
            "_request_timeout": self._config.request_timeout,
        }
        if container is not None:
            request["container"] = container
        if since_seconds is not None:
            request["since_seconds"] = since_seconds

        try:
            with self._api_lock:
                logs = self._core_api.read_namespaced_pod_log(
                    pod_name,
                    self.namespace,
                    **request,
                )
        except Exception as exc:
            self._raise_operation_error(
                "read_namespaced_pod_log",
                "pod",
                pod_name,
                exc,
            )
        if not isinstance(logs, str):
            error = TypeError(
                "Kubernetes pod log response must be str, "
                f"got {type(logs).__name__}"
            )
            self._raise_operation_error(
                "read_namespaced_pod_log",
                "pod",
                pod_name,
                error,
            )
        return logs

    def list_pod_events(
            self,
            pod_name: str,
            *,
            pod_uid: Optional[str] = None,
    ) -> list[PodEventInfo]:
        """Вернуть диагностические события конкретного pod."""

        self._ensure_open()
        self._validate_required_text("pod_name", pod_name)
        self._validate_optional_text("pod_uid", pod_uid)

        selectors = [
            "involvedObject.kind=Pod",
            f"involvedObject.name={pod_name}",
            f"involvedObject.namespace={self.namespace}",
        ]
        if pod_uid is not None:
            selectors.append(f"involvedObject.uid={pod_uid}")

        try:
            with self._api_lock:
                response = self._core_api.list_namespaced_event(
                    self.namespace,
                    field_selector=",".join(selectors),
                    _request_timeout=self._config.request_timeout,
                )
        except Exception as exc:
            self._raise_operation_error(
                "list_namespaced_event",
                "pod_events",
                pod_name,
                exc,
            )

        events = [
            to_pod_event_info(event)
            for event in (getattr(response, "items", None) or [])
        ]
        return sorted(
            events,
            key=lambda event: (
                (
                    event.last_seen_at.isoformat()
                    if event.last_seen_at is not None
                    else ""
                ),
                event.reason or "",
                event.message or "",
            ),
        )

    def delete_pod(
            self,
            pod_name: str,
            *,
            grace_period_seconds: Optional[int] = None,
            expected_uid: Optional[str] = None,
    ) -> None:
        """Запросить удаление pod; опционально защититься UID-precondition."""

        self._ensure_open()
        self._validate_required_text("pod_name", pod_name)
        self._validate_optional_text("expected_uid", expected_uid)
        if grace_period_seconds is not None:
            self._validate_non_negative_int(
                "grace_period_seconds",
                grace_period_seconds,
            )

        request: dict[str, Any] = {
            "_request_timeout": self._config.request_timeout,
        }
        if grace_period_seconds is not None:
            request["grace_period_seconds"] = grace_period_seconds
        if expected_uid is not None:
            request["body"] = {
                "apiVersion": "v1",
                "kind": "DeleteOptions",
                "preconditions": {"uid": expected_uid},
            }

        try:
            with self._api_lock:
                self._core_api.delete_namespaced_pod(
                    pod_name,
                    self.namespace,
                    **request,
                )
        except Exception as exc:
            self._raise_operation_error(
                "delete_namespaced_pod",
                "pod",
                pod_name,
                exc,
            )

        log_event(
            logger,
            logging.INFO,
            "openshift_pod_delete_requested",
            namespace=self.namespace,
            pod=pod_name,
            expected_uid=expected_uid,
            grace_period_seconds=(
                grace_period_seconds
                if grace_period_seconds is not None
                else None
            ),
        )

    def wait_for_pod_ready(
            self,
            pod_name: str,
            *,
            timeout: Optional[float] = None,
            poll_interval: Optional[float] = None,
    ) -> PodInfo:
        """Дождаться ``Running`` pod с condition ``Ready=True``."""

        self._ensure_open()
        self._validate_required_text("pod_name", pod_name)
        effective_timeout, effective_interval = self._wait_settings(
            timeout,
            poll_interval,
        )
        deadline = self._clock.monotonic() + effective_timeout
        last_observed = "pod not found"

        while True:
            try:
                pod = to_pod_info(self._read_pod(pod_name))
                last_observed = self._pod_summary(pod)
                if pod.ready:
                    return pod
            except Exception as exc:
                if self._is_not_found(exc):
                    last_observed = "pod not found"
                elif self._is_retryable_wait_error(
                        "wait_for_pod_ready",
                        exc,
                ):
                    last_observed = self._wait_error_summary(exc)
                else:
                    self._raise_operation_error(
                        "read_namespaced_pod",
                        "pod",
                        pod_name,
                        exc,
                    )

            if not self._sleep_until_next_poll(
                    deadline,
                    effective_interval,
            ):
                raise OpenShiftWaitTimeoutError(
                    f"wait_for_pod_ready:{pod_name}",
                    self.namespace,
                    effective_timeout,
                    last_observed=last_observed,
                )

    def wait_for_replacement_pod(
            self,
            label_selector: Optional[str] = None,
            *,
            name_pattern: Optional[str] = None,
            excluded_uids: AbstractSet[str],
            expected_controller_uid: Optional[str] = None,
            timeout: Optional[float] = None,
            poll_interval: Optional[float] = None,
    ) -> PodInfo:
        """Дождаться нового Ready pod того же контроллера."""

        self._ensure_open()
        self._validate_optional_text("label_selector", label_selector)
        self._validate_optional_text("name_pattern", name_pattern)
        self._validate_optional_text(
            "expected_controller_uid",
            expected_controller_uid,
        )
        if label_selector is None and name_pattern is None:
            raise ValueError(
                "label_selector or name_pattern must be provided"
            )
        if not isinstance(excluded_uids, AbstractSet) or any(
                not isinstance(uid, str) or not uid
                for uid in excluded_uids
        ):
            raise ValueError(
                "excluded_uids must be a set of non-empty strings"
            )
        effective_timeout, effective_interval = self._wait_settings(
            timeout,
            poll_interval,
        )
        deadline = self._clock.monotonic() + effective_timeout
        last_observed = "no pods"

        while True:
            try:
                pods = (
                    self.find_pods(
                        name_pattern,
                        label_selector=label_selector,
                    )
                    if name_pattern is not None
                    else self.list_pods(label_selector=label_selector)
                )
                last_observed = self._pods_summary(pods)
                replacements = [
                    pod
                    for pod in pods
                    if pod.uid is not None
                    and pod.uid not in excluded_uids
                    and pod.ready
                    and (
                        expected_controller_uid is None
                        or pod.controller_uid == expected_controller_uid
                    )
                ]
                if replacements:
                    return sorted(
                        replacements,
                        key=lambda pod: pod.name,
                    )[0]
            except OpenShiftOperationError as exc:
                if not self._is_retryable_wait_error(
                        "wait_for_replacement_pod",
                        exc,
                ):
                    raise
                last_observed = self._wait_error_summary(exc)

            if not self._sleep_until_next_poll(
                    deadline,
                    effective_interval,
            ):
                raise OpenShiftWaitTimeoutError(
                    "wait_for_replacement_pod",
                    self.namespace,
                    effective_timeout,
                    last_observed=last_observed,
                )

    def restart_pod(
            self,
            pod_name: str,
            *,
            label_selector: str,
            grace_period_seconds: Optional[int] = None,
            timeout: Optional[float] = None,
            poll_interval: Optional[float] = None,
    ) -> PodRestartResult:
        """Удалить pod и дождаться Ready-замены с новым UID.

        Метод предназначен только для pod под управлением Deployment,
        StatefulSet или другого контроллера, который создаёт замену.
        """

        self._ensure_open()
        self._validate_required_text("pod_name", pod_name)
        self._validate_required_text("label_selector", label_selector)
        if grace_period_seconds is not None:
            self._validate_non_negative_int(
                "grace_period_seconds",
                grace_period_seconds,
            )
        effective_timeout, effective_interval = self._wait_settings(
            timeout,
            poll_interval,
        )

        existing_pods = self.list_pods(label_selector=label_selector)
        matching = [pod for pod in existing_pods if pod.name == pod_name]
        if not matching:
            raise ValueError(
                f"label_selector does not select pod {pod_name!r}"
            )
        previous = matching[0]
        return self._restart_selected_pod(
            previous,
            existing_pods=existing_pods,
            label_selector=label_selector,
            name_pattern=None,
            grace_period_seconds=grace_period_seconds,
            timeout=effective_timeout,
            poll_interval=effective_interval,
        )

    def restart_pod_by_pattern(
            self,
            name_pattern: str,
            *,
            label_selector: Optional[str] = None,
            grace_period_seconds: Optional[int] = None,
            timeout: Optional[float] = None,
            poll_interval: Optional[float] = None,
    ) -> PodRestartResult:
        """Перезапустить единственный Ready pod по glob его имени."""

        self._ensure_open()
        self._validate_required_text("name_pattern", name_pattern)
        self._validate_optional_text("label_selector", label_selector)
        if grace_period_seconds is not None:
            self._validate_non_negative_int(
                "grace_period_seconds",
                grace_period_seconds,
            )
        effective_timeout, effective_interval = self._wait_settings(
            timeout,
            poll_interval,
        )

        existing_pods = self.find_pods(
            name_pattern,
            label_selector=label_selector,
        )
        previous = self._select_single_pod(
            existing_pods,
            name_pattern=name_pattern,
            ready_only=True,
        )
        return self._restart_selected_pod(
            previous,
            existing_pods=existing_pods,
            label_selector=label_selector,
            name_pattern=name_pattern,
            grace_period_seconds=grace_period_seconds,
            timeout=effective_timeout,
            poll_interval=effective_interval,
        )

    def _restart_selected_pod(
            self,
            previous: PodInfo,
            *,
            existing_pods: list[PodInfo],
            label_selector: Optional[str],
            name_pattern: Optional[str],
            grace_period_seconds: Optional[int],
            timeout: float,
            poll_interval: float,
    ) -> PodRestartResult:
        existing_uids = {
            pod.uid
            for pod in existing_pods
            if pod.uid is not None
        }
        if previous.uid is None:
            raise OpenShiftOperationError(
                "restart_pod",
                self.namespace,
                "pod",
                resource_name=previous.name,
                reason="pod UID is missing",
            )
        if previous.controller_uid is None:
            raise OpenShiftOperationError(
                "restart_pod",
                self.namespace,
                "pod",
                resource_name=previous.name,
                reason="pod is not managed by a controller",
            )

        self.delete_pod(
            previous.name,
            grace_period_seconds=grace_period_seconds,
            expected_uid=previous.uid,
        )
        replacement = self.wait_for_replacement_pod(
            label_selector,
            name_pattern=name_pattern,
            excluded_uids=existing_uids,
            expected_controller_uid=previous.controller_uid,
            timeout=timeout,
            poll_interval=poll_interval,
        )
        log_event(
            logger,
            logging.INFO,
            "openshift_pod_restarted",
            namespace=self.namespace,
            previous_pod=previous.name,
            previous_uid=previous.uid,
            replacement_pod=replacement.name,
            replacement_uid=replacement.uid,
        )
        return PodRestartResult(
            previous=previous,
            replacement=replacement,
        )

    def _select_single_pod(
            self,
            pods: list[PodInfo],
            *,
            name_pattern: str,
            ready_only: bool,
    ) -> PodInfo:
        candidates = [
            pod
            for pod in pods
            if pod.ready or not ready_only
        ]
        if len(candidates) != 1:
            log_event(
                logger,
                logging.WARNING,
                "openshift_pod_selection_failed",
                namespace=self.namespace,
                name_pattern=name_pattern,
                ready_only=ready_only,
                matches=[pod.name for pod in candidates],
            )
            raise OpenShiftPodSelectionError(
                self.namespace,
                name_pattern,
                tuple(pod.name for pod in candidates),
                ready_only=ready_only,
            )
        return candidates[0]

    def _read_pod(self, pod_name: str) -> Any:
        with self._api_lock:
            return self._core_api.read_namespaced_pod(
                pod_name,
                self.namespace,
                _request_timeout=self._config.request_timeout,
            )

    def _wait_settings(
            self,
            timeout: Optional[float],
            poll_interval: Optional[float],
    ) -> tuple[float, float]:
        effective_timeout = (
            self._config.wait_timeout
            if timeout is None
            else timeout
        )
        effective_interval = (
            self._config.poll_interval
            if poll_interval is None
            else poll_interval
        )
        self._validate_positive_number("timeout", effective_timeout)
        self._validate_positive_number(
            "poll_interval",
            effective_interval,
        )
        return float(effective_timeout), float(effective_interval)

    def _sleep_until_next_poll(
            self,
            deadline: float,
            poll_interval: float,
    ) -> bool:
        remaining = deadline - self._clock.monotonic()
        if remaining <= 0:
            return False
        self._clock.sleep(min(poll_interval, remaining))
        return True

    @staticmethod
    def _pod_summary(pod: PodInfo) -> str:
        return (
            f"{pod.name}:phase={pod.phase or '-'}:"
            f"ready={str(pod.ready).lower()}:"
            f"terminating={str(pod.terminating).lower()}:"
            f"reason={pod.reason or '-'}"
        )

    @classmethod
    def _pods_summary(cls, pods: list[PodInfo]) -> str:
        if not pods:
            return "no pods"
        return "; ".join(cls._pod_summary(pod) for pod in pods)

    def _is_retryable_wait_error(
            self,
            operation: str,
            exc: Exception,
    ) -> bool:
        status = getattr(exc, "status", None)
        cause_type = (
            getattr(exc, "cause_type", None)
            or type(exc).__name__
        )
        decision = classify_wait_error(exc)
        if decision.retry:
            log_event(
                logger,
                logging.WARNING,
                "openshift_wait_api_error_retried",
                operation=operation,
                namespace=self.namespace,
                status=status,
                cause_type=cause_type,
                retry_reason=decision.reason,
            )
        elif decision.reason == "tls_certificate_validation":
            log_event(
                logger,
                logging.ERROR,
                "openshift_wait_api_error_not_retried",
                operation=operation,
                namespace=self.namespace,
                status=status,
                cause_type=cause_type,
                retry_reason=decision.reason,
            )
        return decision.retry

    @staticmethod
    def _wait_error_summary(exc: Exception) -> str:
        status = getattr(exc, "status", None)
        cause_type = (
            getattr(exc, "cause_type", None)
            or type(exc).__name__
        )
        return f"api error status={status!r} cause_type={cause_type!r}"

    def _raise_operation_error(
            self,
            operation: str,
            resource: str,
            resource_name: Optional[str],
            exc: Exception,
    ) -> NoReturn:
        status, reason, request_id = self._sdk_error_details(exc)
        log_event(
            logger,
            logging.WARNING,
            "openshift_operation_failed",
            operation=operation,
            namespace=self.namespace,
            resource=resource,
            resource_name=resource_name,
            cause_type=type(exc).__name__,
            status=status,
            reason=reason,
            request_id=request_id,
        )
        raise OpenShiftOperationError(
            operation,
            self.namespace,
            resource,
            resource_name=resource_name,
            cause_type=type(exc).__name__,
            status=status,
            reason=reason,
            request_id=request_id,
        ) from exc

    @staticmethod
    def _sdk_error_details(
            exc: Exception,
    ) -> tuple[Optional[int], Optional[str], Optional[str]]:
        raw_status = getattr(exc, "status", None)
        status = (
            raw_status
            if isinstance(raw_status, int)
            and not isinstance(raw_status, bool)
            else None
        )
        reason = OpenShiftClient._optional_string(
            getattr(exc, "reason", None)
        )
        headers = getattr(exc, "headers", None)
        request_id = None
        if isinstance(headers, Mapping):
            for name in ("Audit-Id", "X-Request-Id", "X-OpenShift-Request-Id"):
                value = headers.get(name)
                if value is not None:
                    request_id = str(value)
                    break
        return status, reason, request_id

    @staticmethod
    def _is_not_found(exc: Exception) -> bool:
        return getattr(exc, "status", None) == 404

    def _ensure_open(self) -> None:
        if self._closed:
            raise OpenShiftClientClosedError(
                f"OpenShift client is closed: namespace={self.namespace!r}"
            )

    @staticmethod
    def _validate_required_text(name: str, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must not be empty")

    @staticmethod
    def _validate_optional_text(
            name: str,
            value: Optional[str],
    ) -> None:
        if value is not None:
            OpenShiftClient._validate_required_text(name, value)

    @staticmethod
    def _validate_positive_int(name: str, value: int) -> None:
        if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 1
        ):
            raise ValueError(f"{name} must be a positive integer")

    @staticmethod
    def _validate_non_negative_int(name: str, value: int) -> None:
        if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
        ):
            raise ValueError(f"{name} must be a non-negative integer")

    @staticmethod
    def _validate_bool(name: str, value: bool) -> None:
        if not isinstance(value, bool):
            raise ValueError(f"{name} must be bool")

    @staticmethod
    def _validate_command(command: Sequence[str]) -> tuple[str, ...]:
        if (
                isinstance(command, (str, bytes))
                or not isinstance(command, Sequence)
        ):
            raise ValueError("command must be a sequence of strings")
        normalized = tuple(command)
        if not normalized:
            raise ValueError("command must not be empty")
        if any(not isinstance(argument, str) for argument in normalized):
            raise ValueError("command must contain only strings")
        if not normalized[0].strip():
            raise ValueError("command executable must not be empty")
        return normalized

    @staticmethod
    def _validate_positive_number(name: str, value: float) -> None:
        if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value <= 0
        ):
            raise ValueError(f"{name} must be greater than zero")

    @staticmethod
    def _optional_string(value: Any) -> Optional[str]:
        return str(value) if value is not None else None
