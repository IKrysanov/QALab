import logging
import time
from typing import Optional

import allure
from httpx import Response

from .helpers.functions import truncate, mask_body, mask_headers
from .constants import SENSITIVE_HEADERS
from utils.curl import to_curl


class RequestLogger:
    """
    Логирование HTTP-запросов и ответов: в стандартный logger и в Allure.

    Изолирован от транспорта, может быть подменён в тестах или расширен
    (например, JSONL-логи, OpenTelemetry-span'ы и т.д.).
    """

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        max_body_size: int = 2000,
    ):
        self._logger = logger or logging.getLogger("async_api_client")
        self._max_body = max_body_size

    def log_request(self, request_id, method, path, headers, kwargs) -> None:
        params = kwargs.get("params")
        raw_body = kwargs.get("json") if kwargs.get("json") is not None else kwargs.get("data")
        files = kwargs.get("files")

        safe_headers = mask_headers(headers)
        safe_body = mask_body(raw_body)
        body_log = truncate(str(safe_body), self._max_body) if safe_body is not None else None

        self._logger.info(
            "→ [%s] %s %s | headers=%s | params=%s | body=%s%s",
            request_id, method, path, safe_headers, params, body_log,
            f" | files={list(files.keys())}" if files else "",
        )

        parts = [f"{method} {path}", f"Headers: {safe_headers}"]
        if params is not None:
            parts.append(f"Query params: {params}")
        if safe_body is not None:
            parts.append(f"Body: {body_log}")
        if files:
            parts.append(f"Files: {list(files.keys())}")

        allure.attach(
            "\n".join(parts),
            name=f"Request {method} {path}",
            attachment_type=allure.attachment_type.TEXT,
        )

    def log_response(self, request_id: str, response: Response, start: float) -> None:
        elapsed_ms = (time.monotonic() - start) * 1000
        self._logger.info(
            "← [%s] %s %s | %d | %.1fms | %d bytes",
            request_id, response.request.method, response.request.url.path,
            response.status_code, elapsed_ms, len(response.content),
        )
        try:
            body_str = truncate(str(response.json()), self._max_body)
            atype = allure.attachment_type.JSON
        except ValueError:
            body_str = truncate(response.text, self._max_body)
            atype = allure.attachment_type.TEXT
        payload = (
            f"Status: {response.status_code}\n"
            f"Elapsed: {elapsed_ms:.1f}ms\n"
            f"Headers: {dict(response.headers)}\n\n{body_str}"
        )
        allure.attach(payload, name="Response", attachment_type=atype)
        allure.attach(
            to_curl(response.request, sensitive_headers=SENSITIVE_HEADERS),
            name="cURL",
            attachment_type=allure.attachment_type.TEXT,
        )

    def log_failure(self, request_id: str, method: str, path: str, start: float, exc: Exception) -> None:
        elapsed_ms = (time.monotonic() - start) * 1000
        self._logger.error(
            "✗ [%s] %s %s | %.1fms | %s: %s",
            request_id, method, path, elapsed_ms, type(exc).__name__, exc,
        )