import json
import time
from src.utils.validator_json.validator import ResponseValidator
import requests
from requests import Session, Response
from requests.auth import HTTPBasicAuth
import allure
from curlify import to_curl

from http import HTTPStatus

from typing import Any, Dict, Optional, Union
from urllib.parse import urljoin
from dotenv import load_dotenv
import os

import logging

logger = logging.getLogger(__name__)

load_dotenv()


def log_redirects(response: Response, *args, **kwargs) -> Response:
    if response.is_redirect:
        logger.info(f"Redirected to: {response.headers.get('Location')}")
        allure.attach(
            to_curl(response.request),
            name="Redirect Request",
            attachment_type=allure.attachment_type.TEXT
        )

    return response


class APIClient:
    MAX_RESPONSE_TIME = 10

    def __init__(
            self,
            session: Session = None,
            base_url: str = os.getenv("BASE_URL"),
            schema: str = "https",
            port: Optional[Union[int, str]] = "",
            cert: Optional[str] = None,
            verify: Optional[Union[int, bool]] = False,
            expect_status: int = HTTPStatus.OK,
            assert_status: bool = True,
            validator: bool = True,
            log_info: bool = True,
            debug: bool = False,
            endpoint_prefix: str = "",
            headers: Optional[Dict[str, str]] = None,
            timeout: int = 10,
            **kwargs,
    ):
        self.session = session or requests.Session()
        self.base_url = base_url
        self.schema = schema
        self.port = port
        self.cert = cert
        self.verify = verify
        self.expect_status = expect_status
        self.assert_status = assert_status
        self.validator = validator
        self.validate_response = ResponseValidator()
        self.log_info = log_info
        self.debug = debug
        self.endpoint_prefix = endpoint_prefix
        self.default_headers = headers or {}
        self.timeout = timeout

    def _request(
            self,
            method: str,
            path: str,
            schema: dict | None = None,
            assert_time: bool = False,
            **kwargs: Any
    ) -> Response:
        validator = kwargs.pop("validator", self.validate_response)
        expected_status = kwargs.pop("expected_status", self.expect_status)
        assert_status = kwargs.pop("assert_status", self.assert_status)
        log_info = kwargs.pop("log_info", self.log_info)
        debug = kwargs.pop("debug", self.debug)
        headers = kwargs.pop("headers", {})
        timeout = kwargs.pop("timeout", self.timeout)

        combined_headers = {**self.default_headers, **headers}
        kwargs["headers"] = combined_headers

        base = f"{self.schema}://{self.base_url}"
        if self.port:
            base += f":{self.port}"

        url = urljoin(base + self.endpoint_prefix + "/", path.lstrip("/"))

        if log_info:
            logger.info(f"Request url: {url}")

        kwargs["hooks"] = {
            "response": log_redirects
        }

        if debug:
            breakpoint()

        start_time = time.time()
        response = self.session.request(
            method.upper(), url, verify=self.verify, cert=self.cert, timeout=timeout, **kwargs
        )
        end_time = time.time()
        response_time = end_time - start_time
        if log_info:
            logger.info(f"Request method: {method.upper()}")
            logger.info(f"Request headers: {combined_headers}")
            logger.info(f"Request body: {kwargs.get('data', kwargs.get('json', ''))}")
            logger.info(f"Response status code: {response.status_code}")
            logger.info(f"Response body: {response.text[:200]}...")
            logger.info(f"Response headers: {response.headers}")

        status_code = response.status_code

        if response_time < self.MAX_RESPONSE_TIME:
            logger.info(f"Response time: {response_time:.2f} seconds")
        else:
            logger.warning(f"Response time exceeded: {response_time:.2f} seconds")

        response_info = {
            "url": url,
            "final_url": response.url,
            "method": method.upper(),
            "status_code": status_code,
            "response_time": response_time,
            "history_redirects": [resp.url for resp in response.history],
            "cookies": response.cookies.get_dict(),
            "headers": dict(response.headers),
            "body": response.text
        }

        allure.attach(
            json.dumps(response_info, indent=4, ensure_ascii=False),
            name="Response Info",
            attachment_type=allure.attachment_type.TEXT
        )
        allure.attach(
            to_curl(response.request),
            name="cURL Request",
            attachment_type=allure.attachment_type.TEXT
        )

        if assert_status:
            with allure.step("Assert status code"):
                allure.attach(
                    str(response.status_code), name="Status Code", attachment_type=allure.attachment_type.TEXT
                )
                assert status_code == expected_status, f"Expected status {expected_status}, got {status_code}"

        if validator:
            content_type = response.headers.get("Content-Type", "").lower()
            if "application/json" not in content_type:
                raise ApiError(f"Unexpected Content-Type: {content_type}", response=response)

            response_json = None

            if response.content:
                try:
                    response_json = response.json()
                except Exception as e:
                    raise ApiError(f"Response content is not valid JSON: {e}", response=response)

            if 200 <= status_code < 300:
                if status_code == 204:
                    if response.content:
                        raise ApiError(
                            "Expected no content for 204 response, but got content.", response=response
                        )
                elif schema:
                    self.validate_response.validate_success(response_json, schema)

            elif 400 <= status_code < 500:
                if schema:
                    self.validate_response.validate_failure(response_json, schema)
                else:
                    self.validate_response.validate_default(status_code, response_json)

            elif 500 <= status_code < 600:
                if schema:
                    self.validate_response.validate_failure(response_json, schema)
                else:
                    self.validate_response.validate_default(status_code, response_json)

        if assert_time:
            with allure.step("Assert response time"):
                allure.attach(
                    f"{response_time} sec.", name="Response Time", attachment_type=allure.attachment_type.TEXT
                )
                assert response_time < self.MAX_RESPONSE_TIME, f"Response time exceeded: {response_time:.2f} seconds"

        return response

    @allure.step("Setting basic authentication for session")
    def basic_auth(self, username: str, password: str):
        self.session.auth = HTTPBasicAuth(username, password)

    @allure.step("Setting bearer token authentication for session")
    def set_bearer_token(self, token: str):
        self.default_headers["Authorization"] = f"Bearer {token}"

    @allure.step("Performing GET request {path}")
    def get(self, path: str, **kwargs: Any) -> Response:
        return self._request("GET", path, **kwargs)

    @allure.step("Performing POST request {path}")
    def post(self, path: str, **kwargs: Any) -> Response:
        return self._request("POST", path, **kwargs)

    @allure.step("Performing PUT request {path}")
    def put(self, path: str, **kwargs: Any) -> Response:
        return self._request("PUT", path, **kwargs)

    @allure.step("Performing PATCH request {path}")
    def patch(self, path: str, **kwargs: Any) -> Response:
        return self._request("PATCH", path, **kwargs)

    @allure.step("Performing DELETE request {path}")
    def delete(self, path: str, **kwargs: Any) -> Response:
        return self._request("DELETE", path, **kwargs)

    @allure.step("Performing OPTIONS request {path}")
    def options(self, path: str, **kwargs: Any) -> Response:
        return self._request("OPTIONS", path, **kwargs)

    @allure.step("Performing HEAD request {path}")
    def head(self, path: str, **kwargs: Any) -> Response:
        return self._request("HEAD", path, **kwargs)

    @allure.step("Closing session")
    def close(self) -> None:
        if self.session:
            self.session.close()
            logger.info("Session closed.")
        else:
            logger.warning("No session to close.")

    @allure.step("Downloading file from {path}")
    def download_file(self, path: str, save_to: str, **kwargs: Any) -> None:
        response = self._request("GET", path, stream=True, **kwargs)

        if response.status_code == HTTPStatus.OK:
            with open(save_to, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info(f"File downloaded and saved to: {save_to}")
        else:
            raise ApiError("Failed to download file", response.status_code, response)

    @allure.step("Uploading file to {path}")
    def upload_file(self, path: str, file_field: str, file_path: str, **kwargs: Any) -> Response:
        with open(file_path, 'rb') as f:
            files = {file_field: f}
            return self._request("POST", path, files=files, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        if exc_type is not None:
            logger.error(f"Exception occurred: {exc_val}")
        return False


class ApiError(Exception):
    """Custom exception for API errors."""

    def __init__(self, message: str = "API error occurred", status_code: int = None, response: Response = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response
