import logging
from http.cookiejar import debug
from typing import Any, Dict

from requests import Response

from src.clients_http.exceptions import ApiError

import json

import allure
import jsonschema

from schemas.default_schemas import DEFAULT_SCHEMAS

logger = logging.getLogger(__name__)


class ResponseValidatorJSON:
    @classmethod
    def validate_response(
            cls, status_code: int, response: Response, schema: Dict[str, Any] = None, validator: bool = True) -> None:
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
                    cls._validate_success(response_json, schema)

            elif 400 <= status_code < 500:
                if schema:
                    cls._validate_failure(response_json, schema)
                else:
                    cls._validate_default(status_code, response_json)

            elif 500 <= status_code < 600:
                if schema:
                    cls._validate_failure(response_json, schema)
                else:
                    cls._validate_default(status_code, response_json)
        else:
            logger.warning("Response validation is disabled. Skipping validation...")
            return

    @classmethod
    def _validate_success(cls, response_data: Dict[str, Any], schema: Dict[str, Any]) -> None:
        with allure.step('Validating response 2xx'):
            cls._validate(response_data, schema)

    @classmethod
    def _validate_failure(cls, response_data: Dict[str, Any], schema: Dict[str, Any]) -> None:
        with allure.step('Validating response 4xx'):
            cls._validate(response_data, schema)

    @classmethod
    def _validate_default(cls, status_code: int, response_data: Dict[str, Any]) -> None:
        with allure.step(f'Validating response {status_code}'):
            schema = DEFAULT_SCHEMAS.get(status_code)
            if not schema:
                logging.warning(f"No default schema found for status code {status_code}...")
                return

            cls._validate(response_data, schema)

    @classmethod
    def _validate(cls, data: Dict[str, Any], schema: Dict[str, Any]):
        try:
            logging.info(f'Validating response with schema: {schema}')
            with allure.step('Validating data'):
                allure.attach(
                    body=json.dumps(data),
                    name='Validating response',
                    attachment_type=allure.attachment_type.TEXT
                )

                jsonschema.validate(data, schema)

        except jsonschema.exceptions.ValidationError as e:
            error_msg = f"Schema validation error: {e.message}"
            allure.attach(
                body=str(e),
                name="Validation Error",
                attachment_type=allure.attachment_type.TEXT
            )
            logging.error(error_msg)
            raise AssertionError(error_msg)
