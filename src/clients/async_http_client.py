from os import getenv

import httpx
import logging
import allure
from http import HTTPStatus
from typing import Any, Optional, Dict, Union
from urllib.parse import urljoin

from src.utils.validator_json.validator import ResponseValidator

logger = logging.getLogger(__name__)


class AsyncAPIClient:
    MAX_RESPONSE_TIME = 10

    def __init__(
            self,
            base_url: str = getenv("BASE_URL"),
            schema: str = "https",
            port: Optional[Union[int, str]] = "",
            headers: Optional[Dict[str, str]] = None,
            verify: bool = True,
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

        self.client = httpx.AsyncClient(verify=verify, timeout=timeout)
        self.validate_response = ResponseValidator()

    def _build_url(self, path: str) -> str:
        base = f"{self.schema}://{self.base_url}"
        if self.port:
            base += f":{self.port}"
        return urljoin(base + self.endpoint_prefix + "/", path.lstrip("/"))

    async def _request(
            self,
            method: str,
            path: str,
            schema: dict | None = None,
            assert_time: bool = False,
            **kwargs: Any
    ) -> httpx.Response:
        headers = kwargs.pop("headers", {})
        expected_status = kwargs.pop("expected_status", self.expect_status)
        assert_status = kwargs.pop("assert_status", self.assert_status)

        url = self._build_url(path)
        combined_headers = {**self.default_headers, **headers}
        kwargs["headers"] = combined_headers

        logger.info(f"[{method.upper()}] {url}")

        response = await self.client.request(method, url, **kwargs)
        response_time = response.elapsed.total_seconds()

        logger.info(f"Status: {response.status_code}, Time: {response_time:.2f}s")

        if assert_status:
            assert response.status_code == expected_status, (
                f"Expected {expected_status}, got {response.status_code}"
            )

        if self.validator:
            if "application/json" not in response.headers.get("Content-Type", "").lower():
                raise ApiError("Invalid Content-Type", response=response)

            try:
                response_json = response.json()
            except Exception as e:
                raise ApiError(f"JSON decode error: {e}", response=response)

            if 200 <= response.status_code < 300:
                if response.status_code == 204 and response.content:
                    raise ApiError("Expected no content for 204", response=response)
                if schema:
                    self.validate_response.validate_success(response_json, schema)
            elif 400 <= response.status_code < 600:
                if schema:
                    self.validate_response.validate_failure(response_json, schema)
                else:
                    self.validate_response.validate_default(response.status_code, response_json)

        if assert_time:
            with allure.step("Assert response time"):
                allure.attach(
                    f"{response_time} sec.", name="Response Time", attachment_type=allure.attachment_type.TEXT
                )
                assert response_time < self.MAX_RESPONSE_TIME, f"Response time exceeded: {response_time:.2f} seconds"


        return response

    # Shortcuts
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

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()


class ApiError(Exception):
    def __init__(self, message: str, status_code: int = None, response: httpx.Response = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response
