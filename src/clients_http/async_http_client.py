from enum import verify
from os import getenv

import httpx
import logging
import allure
from http import HTTPStatus
from typing import Any, Optional, Dict, Union
from urllib.parse import urljoin

from src.clients_http.config import ClientsHttpConfig as Config

from src.utils.validation.schema_validator import ResponseValidatorJSON
from src.utils.validation.status_validator import ResponseValidatorStatus
from src.utils.validation.time_validator import ResponseTimeValidator

logger = logging.getLogger(__name__)


class AsyncAPIClient:
    def __init__(
            self,
            base_url: str = Config.BASE_URL,
            schema: str = Config.SCHEMA,
            port: Optional[Union[int, str]] = Config.PORT,
            headers: Optional[Dict[str, str]] = None,
            verify: bool = Config.VERIFY,
            timeout: int = 10,
            expect_status: int = HTTPStatus.OK,
            assert_status: bool = True,
            validator: bool = True,
            endpoint_prefix: str = "",
    ):
        self.base_url = base_url
        self.schema = schema
        self.port = port
        self.verify = verify
        self.timeout = timeout
        self.expect_status = expect_status
        self.assert_status = assert_status
        self.validator = validator
        self.endpoint_prefix = endpoint_prefix
        self.default_headers = headers or {}

        self.session = httpx.AsyncClient(verify=verify, timeout=timeout)

    def _build_url(self, path: str) -> str:
        base = f"{self.schema}://{self.base_url}"
        if self.port:
            base += f":{self.port}"
        return urljoin(base + self.endpoint_prefix + "/", path.lstrip("/"))

    @allure.step("Request to {method} {path} and asserting")
    async def _request(
            self,
            method: str,
            path: str,
            json_schema: dict | None = None,
            **kwargs: Any
    ) -> httpx.Response:
        headers = kwargs.pop("headers", {})
        expected_status = kwargs.pop("expected_status", self.expect_status)
        validator = kwargs.pop("validator", self.validator)
        assert_status = kwargs.pop("assert_status", self.assert_status)
        assert_time = kwargs.pop("assert_time", True)

        combined_headers = {**self.default_headers, **headers}
        kwargs["headers"] = combined_headers

        url = self._build_url(path)

        response = await self.session.request(method, url, **kwargs)
        response_time = response.elapsed.total_seconds()
        status_code = response.status_code

        ResponseValidatorStatus.validate_status(status_code, expected_status, assert_status)
        ResponseValidatorJSON.validate_response(status_code, response, json_schema, validator)
        ResponseTimeValidator.validate_time_response(response_time, assert_time)

        return response

    async def get(self, path: str, **kwargs) -> httpx.Response:
        return await self._request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs) -> httpx.Response:
        return await self._request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs) -> httpx.Response:
        return await self._request("PUT", path, **kwargs)

    async def delete(self, path: str, **kwargs) -> httpx.Response:
        return await self._request("DELETE", path, **kwargs)

    async def patch(self, path: str, **kwargs) -> httpx.Response:
        return await self._request("PATCH", path, **kwargs)

    @allure.step("Closing the API client")
    async def close(self):
        await self.session.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()


class ApiError(Exception):
    def __init__(self, message: str, status_code: int = None, response: httpx.Response = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response
