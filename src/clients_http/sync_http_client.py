import json
import time
from src.utils.validation.schema_validator import ResponseValidatorJSON
from src.utils.validation.status_validator import ResponseValidatorStatus
from src.utils.validation.time_validator import ResponseTimeValidator

from src.clients_http.config import ClientsHttpConfig

from src.clients_http.exceptions import ApiError

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

config = ClientsHttpConfig()


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
    def __init__(
            self,
            session: Session = None,
            base_url: str = config.BASE_URL,
            schema: str = config.SCHEMA,
            port: Optional[Union[int, str]] = config.PORT,
            cert: Optional[str] = config.CERT,
            verify: Optional[Union[int, bool]] = config.VERIFY,
            expect_status: int = HTTPStatus.OK,
            assert_status: bool = True,
            validator: bool = True,
            assert_time: bool = False,
            log_info: bool = True,
            debug: bool = False,
            endpoint_prefix: str = "",
            headers: Optional[Dict[str, str]] = None,
            timeout: int = config.TIMEOUT,
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
        self.assert_time = assert_time
        self.log_info = log_info
        self.debug = debug
        self.endpoint_prefix = endpoint_prefix
        self.default_headers = headers or {}
        self.timeout = timeout

    def _build_url(self, path: str) -> str:
        """Build a URL from the given path."""

        base = f"{self.schema}://{self.base_url}"
        if self.port:
            base += f":{self.port}"
        return urljoin(base + self.endpoint_prefix + "/", path.lstrip("/"))

    def _request(
            self,
            method: str,
            path: str,
            json_schema: dict | None = None,
            **kwargs: Any
    ) -> Response:
        """Make a request."""

        headers = kwargs.pop("headers", {})
        timeout = kwargs.pop("timeout", self.timeout)
        expected_status = kwargs.pop("expected_status", self.expect_status)
        validator = kwargs.pop("validator", self.validator)
        assert_status = kwargs.pop("assert_status", self.assert_status)
        assert_time = kwargs.pop("assert_time", True)

        combined_headers = {**self.default_headers, **headers}
        kwargs["headers"] = combined_headers

        url = self._build_url(path)

        kwargs["hooks"] = {
            "response": log_redirects
        }

        debug = kwargs.pop("debug", self.debug)
        if debug:
            breakpoint()

        start_time = time.time()
        response = self.session.request(
            method.upper(), url, verify=self.verify, cert=self.cert, timeout=timeout, **kwargs
        )
        end_time = time.time()
        response_time = end_time - start_time

        status_code = response.status_code

        log_info = kwargs.pop("log_info", self.log_info)
        if log_info:
            logger.info(f"Request method: {method.upper()}")
            logger.info(f"Request url: {response.request.url}")
            logger.info(f"Request headers: {combined_headers}")
            logger.info(f"Request body: {kwargs.get('data', kwargs.get('json', ''))}")
            logger.info(f"Response status code: {response.status_code}")
            logger.info(f"Response body: {response.text[:200]}...")
            logger.info(f"Response headers: {response.headers}")

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

        ResponseValidatorStatus.validate_status(status_code, expected_status, assert_status)
        ResponseValidatorJSON.validate_response(status_code, response, json_schema, validator)
        ResponseTimeValidator.validate_time_response(response_time, assert_time)

        return response

    @allure.step("Setting basic authentication for session")
    def basic_auth(self, username: str, password: str):
        """Basic authentication for session."""

        self.session.auth = HTTPBasicAuth(username, password)

    @allure.step("Setting bearer token authentication for session")
    def set_bearer_token(self, token: str):
        """Bearer token authentication for session."""

        self.default_headers["Authorization"] = f"Bearer {token}"

    @allure.step("Performing GET request {path}")
    def get(self, path: str, **kwargs: Any) -> Response:
        """Performs a GET request."""

        return self._request("GET", path, **kwargs)

    @allure.step("Performing POST request {path}")
    def post(self, path: str, **kwargs: Any) -> Response:
        """Performs a POST request."""

        return self._request("POST", path, **kwargs)

    @allure.step("Performing PUT request {path}")
    def put(self, path: str, **kwargs: Any) -> Response:
        """Performs a PUT request."""

        return self._request("PUT", path, **kwargs)

    @allure.step("Performing PATCH request {path}")
    def patch(self, path: str, **kwargs: Any) -> Response:
        """Performs a PATCH request."""

        return self._request("PATCH", path, **kwargs)

    @allure.step("Performing DELETE request {path}")
    def delete(self, path: str, **kwargs: Any) -> Response:
        """Performs a DELETE request."""

        return self._request("DELETE", path, **kwargs)

    @allure.step("Performing OPTIONS request {path}")
    def options(self, path: str, **kwargs: Any) -> Response:
        """Performs a OPTIONS request."""

        return self._request("OPTIONS", path, **kwargs)

    @allure.step("Performing HEAD request {path}")
    def head(self, path: str, **kwargs: Any) -> Response:
        """Performs a HEAD request."""

        return self._request("HEAD", path, **kwargs)

    @allure.step("Closing session")
    def close(self) -> None:
        """Close the session."""

        if self.session:
            self.session.close()
            logger.info("Session closed.")
        else:
            logger.warning("No session to close.")

    @allure.step("Downloading file from {path}")
    def download_file(self, path: str, save_to: str, **kwargs: Any) -> None:
        """Download file from {path} to {save_to}."""

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
        """Upload file from {path} to {file_path}."""

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
