import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Optional, Type

import allure
import httpx
from httpx import AsyncClient, Response
from pydantic import BaseModel

from http import HTTPStatus
from src.async_api_client.redirects import RedirectTracker

from . import validators
from .request_logger import RequestLogger

from .config import APIConfig
from .auth import AsyncAuthStrategy, NoAuth
from .types import StatusCode, ResponseModel, RequestModel
from .exceptions import (
    APITimeoutError,
    APITransportError
)

from .constants import DEFAULT_ERROR_MODELS


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

    async def __aenter__(self) -> "AsyncHTTPClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def get(self, path, expected_status=HTTPStatus.OK, response_model=None, **kwargs):
        return await self.request("GET", path, expected_status, response_model, **kwargs)

    async def post(self, path, expected_status=HTTPStatus.CREATED, response_model=None, **kwargs):
        return await self.request("POST", path, expected_status, response_model, **kwargs)

    async def put(self, path, expected_status=HTTPStatus.OK, response_model=None, **kwargs):
        return await self.request("PUT", path, expected_status, response_model, **kwargs)

    async def patch(self, path, expected_status=HTTPStatus.OK, response_model=None, **kwargs):
        return await self.request("PATCH", path, expected_status, response_model, **kwargs)

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

    def __init__(
            self,
            config: APIConfig,
            auth: Optional[AsyncAuthStrategy] = None,
            session: Optional[AsyncClient] = None,
            error_models: Optional[dict[int, Type[BaseModel]]] = None,
            validate_request: bool = True,
            validate_response: bool = True,
            validate_status: bool = True,
            logger: Optional[RequestLogger] = None
    ):
        self._config = config
        self._auth = auth or NoAuth()
        self._owns_session = session is None
        self._error_models = error_models if error_models is not None else DEFAULT_ERROR_MODELS
        self._validate_request = validate_request
        self._validate_response = validate_response
        self._validate_status = validate_status

        self._request_id_header = config.request_trace_id_header
        self._max_log_body = config.max_log_body

        self._req_logger = logger or RequestLogger(max_body_size=config.max_log_body)

        if session is None:
            session = self._build_session()
        self._session = session

    @property
    def session(self) -> AsyncClient:
        return self._session

    async def request(
            self,
            method: str,
            path: str,
            expected_status: StatusCode = HTTPStatus.OK,
            response_model: ResponseModel = None,
            request_model: RequestModel = None,
            validate_request: Optional[bool] = None,
            validate_response: Optional[bool] = None,
            validate_status: Optional[bool] = None,
            follow_redirects: Optional[bool] = None,
            **kwargs: Any,
    ) -> Response:
        method = method.upper()
        request_id = uuid.uuid4().hex[:8]

        do_validate_req = validators.effective(validate_request, default=self._validate_request)
        do_validate_resp = validators.effective(validate_response, default=self._validate_response)
        do_validate_status = validators.effective(validate_status, default=self._validate_status)

        kwargs = validators.prepare_payload(
            kwargs,
            request_model=request_model,
            validate=do_validate_req,
        )

        raw_headers = kwargs.pop("headers", {}) or {}
        raw_headers.setdefault(self._request_id_header, request_id)
        headers = await self._auth.apply(raw_headers)

        if follow_redirects is not None:
            kwargs["follow_redirects"] = follow_redirects

        with allure.step(f"{method} {path}"):
            self._req_logger.log_request(request_id, method, path, headers, kwargs)
            start = time.monotonic()
            try:
                response = await self.session.request(method, path, headers=headers, **kwargs)
            except httpx.TimeoutException as exc:
                self._req_logger.log_failure(request_id, method, path, start, exc)
                raise APITimeoutError(f"Request timeout: {exc}") from exc
            except httpx.RequestError as exc:
                self._req_logger.log_failure(request_id, method, path, start, exc)
                raise APITransportError(f"Network error: {exc}") from exc

            if response.history:
                response.extensions["redirects"] = RedirectTracker.track(response, request_id)
            self._req_logger.log_response(request_id, response, start)

            if do_validate_status:
                validators.assert_status(response, expected_status)

            if do_validate_resp:
                validators.validate_body(response, response_model, self._error_models)

            return response

    async def aclose(self) -> None:
        if self._owns_session:
            await self._session.aclose()

    def _build_session(self) -> AsyncClient:
        limits = httpx.Limits(
            max_connections=self._config.max_connections,
            max_keepalive_connections=self._config.max_keepalive_connections,
        )
        return httpx.AsyncClient(
            base_url=self._config.base_url,
            timeout=self._config.timeout,
            verify=self._config.verify_ssl,
            headers=self._config.default_headers,
            limits=limits,
            follow_redirects=self._config.follow_redirects,
        )
