import logging

from src.clients_http.config import ClientsHttpConfig

import allure

logger = logging.getLogger(__name__)


class ResponseTimeValidator:
    @classmethod
    def validate_time_response(cls, response_time: float, assert_time: bool) -> None:
        expected_time = ClientsHttpConfig.MAX_RESPONSE_TIME
        warning_msg = f"Response time exceeded: {response_time:.2f} seconds"

        if response_time < expected_time:
            logger.info(f"Response time: {response_time:.2f} seconds")
        else:
            logger.warning(warning_msg)

        if assert_time:
            with allure.step("Assert response time"):
                allure.attach(
                    f"{response_time} sec.", name="Response Time", attachment_type=allure.attachment_type.TEXT
                )
                assert response_time < expected_time, warning_msg
        else:
            logger.warning("Response time validation is disabled. Skipping validation...")
            return
