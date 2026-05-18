import logging
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Optional, Type, Union, Iterable

import allure
import httpx
from httpx import AsyncClient, Response
from pydantic import BaseModel, ValidationError

from http import HTTPStatus
from src.async_api_client.redirects import RedirectTracker

from .config import APIConfig
from .auth import AsyncAuthStrategy, NoAuth
from .exceptions import APIError, APITimeoutError
from src.async_api_client.models.models import (
    ErrorResponse,
    ValidationErrorResponse,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    ServerError,
)

from curlify import to_curl

StatusCode = Union[int, Iterable[int], None]
ResponseModel = Optional[Type[BaseModel]]
RequestModel = Optional[Type[BaseModel]]
RequestPayload = Union[BaseModel, dict, None]

SENSITIVE_HEADERS = {"authorization", "x-api-key", "cookie", "set-cookie", "x-auth-token"}

DEFAULT_ERROR_MODELS: dict[int, Type[BaseModel]] = {
    HTTPStatus.BAD_REQUEST: ErrorResponse,
    HTTPStatus.UNAUTHORIZED: UnauthorizedError,
    HTTPStatus.FORBIDDEN: ForbiddenError,
    HTTPStatus.NOT_FOUND: NotFoundError,
    HTTPStatus.CONFLICT: ErrorResponse,
    HTTPStatus.UNPROCESSABLE_CONTENT: ValidationErrorResponse,
    HTTPStatus.INTERNAL_SERVER_ERROR: ServerError,
    HTTPStatus.BAD_GATEWAY: ServerError,
    HTTPStatus.SERVICE_UNAVAILABLE: ServerError,
    HTTPStatus.GATEWAY_TIMEOUT: ServerError,
}


def _mask_headers(headers: dict) -> dict:
    return {
        k: ("***" if k.lower() in SENSITIVE_HEADERS else v)
        for k, v in (headers or {}).items()
    }


class AsyncHTTPClient(ABC):
    @abstractmethod
    async def request(
            self,
            method: str,
            path: str,
            expected_status: StatusCode = HTTPStatus.OK,
            response_model: ResponseModel = None,
            **kwargs: Any,
    ) -> Response: ...

    @abstractmethod
    async def aclose(self) -> None: ...

    @allure.step("async-request GET {path}")
    async def get(self, path, expected_status=HTTPStatus.OK, response_model=None, **kwargs):
        return await self.request("GET", path, expected_status, response_model, **kwargs)

    @allure.step("async-request POST {path}")
    async def post(self, path, expected_status=HTTPStatus.CREATED, response_model=None, **kwargs):
        return await self.request("POST", path, expected_status, response_model, **kwargs)

    @allure.step("async-request PUT {path}")
    async def put(self, path, expected_status=HTTPStatus.OK, response_model=None, **kwargs):
        return await self.request("PUT", path, expected_status, response_model, **kwargs)

    @allure.step("async-request PATCH {path}")
    async def patch(self, path, expected_status=HTTPStatus.OK, response_model=None, **kwargs):
        return await self.request("PATCH", path, expected_status, response_model, **kwargs)

    @allure.step("async-request DELETE {path}")
    async def delete(self, path, expected_status=HTTPStatus.NO_CONTENT, response_model=None, **kwargs):
        return await self.request("DELETE", path, expected_status, response_model, **kwargs)


class HttpxAsyncClient(AsyncHTTPClient):
    """
    Транспорт с встроенным логированием и автовалидацией ответа.

    Валидация ответа:
      • Если передан response_model — валидируем им.
      • Иначе — берём модель из error_models по status_code (401/403/404/422/5xx).
      • Если в реестре нет модели для статуса — пропускаем валидацию.
    """

    logger = logging.getLogger("async_api_client")

    def __init__(
            self,
            config: APIConfig,
            auth: Optional[AsyncAuthStrategy] = None,
            session: Optional[AsyncClient] = None,
            error_models: Optional[dict[int, Type[BaseModel]]] = None,
            validate_request: bool = True,
            validate_response: bool = True,
            validate_status: bool = True,
    ):
        self._config = config
        self._auth = auth or NoAuth()
        self._owns_session = session is None
        self._error_models = error_models if error_models is not None else DEFAULT_ERROR_MODELS
        self._validate_request = validate_request
        self._validate_response = validate_response
        self._validate_status = validate_status

        if session is None:
            limits = httpx.Limits(
                max_connections=config.max_connections,
                max_keepalive_connections=config.max_keepalive_connections,
            )
            session = httpx.AsyncClient(
                base_url=config.base_url,
                timeout=config.timeout,
                verify=config.verify_ssl,
                headers=config.default_headers,
                limits=limits,
                follow_redirects=config.follow_redirects,
            )
        self._session = session

    @property
    def session(self) -> AsyncClient:
        return self._session

    async def request(
            self,
            method: str,
            path: str,
            expected_status: HTTPStatus = HTTPStatus.OK,
            response_model: ResponseModel = None,
            request_model: RequestModel = None,
            validate_request: Optional[bool] = None,
            validate_response: Optional[bool] = None,
            validate_status: Optional[bool] = None,
            follow_redirects: Optional[bool] = None,
            **kwargs: Any,
    ) -> Response:
        do_validate_req = self._effective(validate_request, default=self._validate_request)
        do_validate_resp = self._effective(validate_response, default=self._validate_response)
        do_validate_status = self._effective(validate_status, default=self._validate_status)

        kwargs = self._prepare_payload(
            kwargs,
            request_model=request_model,
            validate=do_validate_req,
        )

        headers = await self._auth.apply(kwargs.pop("headers", {}) or {})
        request_id = uuid.uuid4().hex[:8]

        if follow_redirects is not None:
            kwargs["follow_redirects"] = follow_redirects

        with allure.step(f"{method.upper()} {path}"):
            self._log_request(request_id, method, path, headers, kwargs)

            start = time.monotonic()
            try:
                response = await self.session.request(method, path, headers=headers, **kwargs)
            except httpx.TimeoutException as exc:
                self._log_failure(request_id, method, path, start, exc)
                raise APITimeoutError(f"Request timeout: {exc}") from exc
            except httpx.RequestError as exc:
                self._log_failure(request_id, method, path, start, exc)
                raise APIError(f"Network error: {exc}") from exc

            if response.history:
                response.extensions["redirects"] = RedirectTracker.track(response, request_id)
            self._log_response(request_id, response, start)

            if do_validate_status:
                self._assert_status(response, expected_status)

            if do_validate_resp:
                self._validate_body(response, response_model)

            return response

    # --- Валидация ----------------------------------------------------------

    @staticmethod
    def _effective(per_request: Optional[bool], *, default: bool) -> bool:
        """Вычисляет результирующее булево значение настройки с учётом приоритетов."""

        return default if per_request is None else per_request

    def _prepare_payload(
            self,
            kwargs: dict,
            request_model: RequestModel,
            validate: bool,
    ) -> dict:
        """
        Приводит payload в kwargs['json'] к dict для отправки.

        Поведение:
          - payload — BaseModel: используется model.model_dump(by_alias=True)
              (объект уже валиден — pydantic проверил при создании).
          - payload — dict + request_model + validate=True:
              валидируем dict через модель, при ошибке кидаем AssertionError.
          - payload — dict + validate=False:
              отправляем как есть, не трогая.
        """

        payload = kwargs.get("json")
        if payload is None:
            return kwargs

        if isinstance(payload, BaseModel):
            kwargs["json"] = payload.model_dump(by_alias=True, exclude_none=True)
            return kwargs

        if validate and request_model is not None:
            try:
                model_instance = request_model.model_validate(payload)
            except ValidationError as exc:
                raise AssertionError(
                    f"Request body does not match {request_model.__name__}:\n{exc}\n\n"
                    f"Payload: {payload}"
                ) from exc
            kwargs["json"] = model_instance.model_dump(by_alias=True, exclude_none=True)

        return kwargs

    @staticmethod
    def _assert_status(response: Response, expected: StatusCode) -> None:
        if expected is None:
            return
        if isinstance(expected, (int, HTTPStatus)):
            expected_list = [int(expected)]
        else:
            expected_list = [int(s) for s in expected]
        actual = response.status_code
        assert actual in expected_list, (
            f"Unexpected status code: got {actual}, expected {expected_list}. "
            f"URL: {response.request.url}\nBody: {response.text}"
        )

    def _validate_body(self, response: Response, response_model: ResponseModel) -> None:
        model = response_model or self._error_models.get(response.status_code)
        if model is None:
            return

        if not response.content:
            return

        try:
            body = response.json()
        except ValueError:
            raise AssertionError(
                f"Expected JSON body matching {model.__name__}, "
                f"got non-JSON response: {response.text[:200]}"
            )

        try:
            model.model_validate(body)
        except ValidationError as exc:
            raise AssertionError(
                f"Response body does not match {model.__name__} "
                f"(status {response.status_code}):\n{exc}\n\nBody: {body}"
            ) from exc

    # --- Логирование --------------------------------------------------------

    def _log_request(self, request_id: str, method: str, path: str, headers: dict, kwargs: dict) -> None:
        body = kwargs.get("json") or kwargs.get("data") or kwargs.get("params")
        self.logger.info(
            "→ [%s] %s %s | headers=%s | body=%s",
            request_id, method.upper(), path, _mask_headers(headers), body,
        )
        safe_payload = (
            f"{method.upper()} {path}\n"
            f"Headers: {_mask_headers(headers)}\n"
            f"Body: {body}"
        )
        allure.attach(safe_payload, name="Request", attachment_type=allure.attachment_type.TEXT)

    def _log_response(self, request_id: str, response: Response, start: float) -> None:
        elapsed_ms = (time.monotonic() - start) * 1000
        self.logger.info(
            "← [%s] %s %s | %d | %.1fms | %d bytes",
            request_id, response.request.method, response.request.url.path,
            response.status_code, elapsed_ms, len(response.content),
        )
        try:
            body_str = str(response.json())
            atype = allure.attachment_type.JSON
        except ValueError:
            body_str = response.text
            atype = allure.attachment_type.TEXT
        payload = (
            f"Status: {response.status_code}\n"
            f"Elapsed: {elapsed_ms:.1f}ms\n"
            f"Headers: {dict(response.headers)}\n\n{body_str}"
        )
        allure.attach(payload, name="Response", attachment_type=atype)
        allure.attach(to_curl(response.request), name="cURL", attachment_type=allure.attachment_type.TEXT)

    def _log_failure(self, request_id: str, method: str, path: str, start: float, exc: Exception) -> None:
        elapsed_ms = (time.monotonic() - start) * 1000
        self.logger.error(
            "✗ [%s] %s %s | %.1fms | %s: %s",
            request_id, method.upper(), path, elapsed_ms, type(exc).__name__, exc,
        )

    @allure.step("Close HTTP async-client")
    async def aclose(self) -> None:
        if self._owns_session:
            await self._session.aclose()
