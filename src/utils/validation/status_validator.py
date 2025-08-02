import logging
import allure

logger = logging.getLogger(__name__)


class ResponseValidatorStatus:
    @classmethod
    def validate_status(
            cls, status_code: int, expected_status: int, assert_status: bool = True
    ) -> None:
        with allure.step(f'Validating response status {status_code}'):
            if status_code < 100 or status_code >= 600:
                error_msg = f"Invalid HTTP status code: {status_code}. Must be between 100 and 599."
                allure.attach(
                    body=error_msg,
                    name="Validation Error",
                    attachment_type=allure.attachment_type.TEXT
                )
                logging.error(error_msg)

                raise AssertionError(error_msg)

            logger.info(f"Response status {status_code} is valid.")

            if assert_status:
                with allure.step("Assert status code"):
                    allure.attach(
                        str(status_code), name="Status Code", attachment_type=allure.attachment_type.TEXT
                    )
                    assert status_code == expected_status, f"Expected status {expected_status}, got {status_code}"
            else:
                logger.info(f"Skipping status code assertion. Expected: {expected_status}, Actual: {status_code}")
