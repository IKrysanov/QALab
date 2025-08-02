import logging
from typing import Any, Dict

import allure
import jsonschema

from schemas.default_schemas import DEFAULT_SCHEMAS


class ResponseValidator:
    @classmethod
    def validate_success(cls, response_data: Dict[str, Any], schema: Dict[str, Any]) -> None:
        with allure.step('Validating response 2xx'):
            cls._validate(response_data, schema)

    @classmethod
    def validate_failure(cls, response_data: Dict[str, Any], schema: Dict[str, Any]) -> None:
        with allure.step('Validating response 4xx'):
            cls._validate(response_data, schema)

    @classmethod
    def validate_default(cls, status_code: int, response_data: Dict[str, Any]) -> None:
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
                jsonschema.validate(data, schema)

        except jsonschema.exceptions.ValidationError as e:
            error_msg = f"Schema validation error: {e.message}"
            allure.attach(
                body=str(e),
                name="Validation Error",
                attachment_type=allure.attachment_type.TEXT
            )
            raise AssertionError(error_msg)
