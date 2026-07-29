"""Kubernetes WebSocket transport для неинтерактивного pod exec."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from threading import RLock
from typing import Any, Optional

from .models import CommandResult
from .protocols import CoreV1Service

_CONNECT_TIMEOUT_MESSAGE = "pod exec websocket connect timed out"
_WEBSOCKET_CLASS_LOCK = RLock()


class PodExecTransportTimeoutError(TimeoutError):
    """Внутренний timeout транспорта exec."""


class PodExecTransportOutputTooLargeError(RuntimeError):
    """Внутреннее превышение лимита вывода exec."""


class KubernetesWebSocketConnectTimeout:
    """Ограничивает connect/handshake, который SDK не связывает с timeout."""

    @contextmanager
    def apply(self, timeout: float) -> Iterator[None]:
        """Временно передать socket timeout в ``WebSocket.connect`` SDK."""

        from kubernetes.stream import ws_client
        from websocket import WebSocketTimeoutException

        with _WEBSOCKET_CLASS_LOCK:
            original_websocket = ws_client.WebSocket

            class BoundedConnectWebSocket(original_websocket):
                def connect(self, url: str, **options: Any) -> Any:
                    options.setdefault("timeout", timeout)
                    try:
                        return super().connect(url, **options)
                    except (
                            TimeoutError,
                            WebSocketTimeoutException,
                    ) as exc:
                        raise PodExecTransportTimeoutError(
                            _CONNECT_TIMEOUT_MESSAGE
                        ) from exc

            ws_client.WebSocket = BoundedConnectWebSocket
            try:
                yield
            finally:
                ws_client.WebSocket = original_websocket


class KubernetesPodExecutor:
    """Выполняет команду через ``kubernetes.stream`` с bounded output."""

    def __init__(
            self,
            core_api: CoreV1Service,
            *,
            stream_function: Optional[Callable[..., Any]] = None,
            monotonic: Callable[[], float] = time.monotonic,
            connect_timeout: Optional[
                KubernetesWebSocketConnectTimeout
            ] = None,
    ) -> None:
        self._core_api = core_api
        self._stream_function = stream_function
        self._monotonic = monotonic
        self._connect_timeout = (
            connect_timeout
            or KubernetesWebSocketConnectTimeout()
        )

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
        stream_function = self._stream_function
        if stream_function is None:
            from kubernetes.stream import stream

            stream_function = stream

        started_at = self._monotonic()
        try:
            with self._connect_timeout.apply(timeout):
                websocket = stream_function(
                    self._core_api.connect_post_namespaced_pod_exec,
                    pod_name,
                    namespace,
                    command=list(command),
                    container=container_name,
                    stderr=True,
                    stdin=False,
                    stdout=True,
                    tty=False,
                    _preload_content=False,
                    _request_timeout=timeout,
                )
        except PodExecTransportTimeoutError:
            raise
        except Exception as exc:
            if (
                    getattr(exc, "status", None) == 0
                    and getattr(exc, "reason", None)
                    == _CONNECT_TIMEOUT_MESSAGE
            ):
                raise PodExecTransportTimeoutError(
                    _CONNECT_TIMEOUT_MESSAGE
                ) from exc
            raise
        try:
            self._validate_websocket(websocket)
        except Exception:
            close = getattr(websocket, "close", None)
            if callable(close):
                close()
            raise

        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []
        output_size = 0
        deadline = started_at + timeout

        try:
            while websocket.is_open():
                remaining = deadline - self._monotonic()
                if remaining <= 0:
                    raise PodExecTransportTimeoutError(
                        f"pod exec exceeded timeout={timeout}"
                    )
                websocket.update(timeout=min(1.0, remaining))
                output_size = self._drain_output(
                    websocket,
                    stdout_chunks,
                    stderr_chunks,
                    output_size,
                    output_limit_bytes,
                )

            self._drain_output(
                websocket,
                stdout_chunks,
                stderr_chunks,
                output_size,
                output_limit_bytes,
            )
            exit_code = websocket.returncode
            if (
                    isinstance(exit_code, bool)
                    or not isinstance(exit_code, int)
            ):
                raise RuntimeError(
                    "Kubernetes exec response has no integer exit code"
                )
        finally:
            websocket.close()

        return CommandResult(
            namespace=namespace,
            pod_name=pod_name,
            container_name=container_name,
            command=tuple(command),
            stdout="".join(stdout_chunks),
            stderr="".join(stderr_chunks),
            exit_code=exit_code,
            duration_seconds=max(
                0.0,
                self._monotonic() - started_at,
            ),
        )

    @staticmethod
    def _drain_output(
            websocket: Any,
            stdout_chunks: list[str],
            stderr_chunks: list[str],
            current_size: int,
            output_limit_bytes: int,
    ) -> int:
        stdout = websocket.read_stdout(timeout=0)
        stderr = websocket.read_stderr(timeout=0)
        if not isinstance(stdout, str) or not isinstance(stderr, str):
            raise TypeError("Kubernetes exec output must be text")

        stdout_chunks.append(stdout)
        stderr_chunks.append(stderr)
        current_size += len(stdout.encode("utf-8"))
        current_size += len(stderr.encode("utf-8"))
        if current_size > output_limit_bytes:
            raise PodExecTransportOutputTooLargeError(
                "pod exec output exceeded "
                f"limit_bytes={output_limit_bytes}"
            )
        return current_size

    @staticmethod
    def _validate_websocket(websocket: Any) -> None:
        required_members = (
            "close",
            "is_open",
            "read_stderr",
            "read_stdout",
            "returncode",
            "update",
        )
        missing = [
            member
            for member in required_members
            if not hasattr(websocket, member)
        ]
        if missing:
            raise TypeError(
                "kubernetes.stream returned an invalid WebSocket client: "
                f"missing={missing!r}"
            )
