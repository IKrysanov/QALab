import logging
from http import HTTPStatus
from typing import Type, Optional

from httpx import Response
from pydantic import BaseModel, ValidationError

from .exceptions import (
    StatusAssertionError,
    RequestValidationError,
    ResponseValidationError,
)
from .types import StatusCode, ResponseModel, RequestModel

logger = logging.getLogger("async_api_client")


def prepare_payload(kwargs: dict, request_model: RequestModel, validate: bool) -> dict:
    """Сериализует Pydantic-модель в dict для отправки, опционально валидируя сырой dict."""

    payload = kwargs.get("json")
    if payload is None:
        return kwargs

    if isinstance(payload, BaseModel):
        kwargs["json"] = payload.model_dump(by_alias=True, exclude_none=True)
        return kwargs

    if validate:
        if request_model is None:
            raise RequestValidationError(
                "Cannot validate dict payload without request_model. ..."
            )
        try:
            model_instance = request_model.model_validate(payload)
        except ValidationError as exc:
            raise RequestValidationError(
                f"Request body does not match {request_model.__name__}:\n{exc}"
            ) from exc
        kwargs["json"] = model_instance.model_dump(by_alias=True, exclude_none=True)

    return kwargs


def assert_status(response: Response, expected: StatusCode) -> None:
    """Проверяет, что статус-код входит в список ожидаемых."""

    if expected is None:
        return

    if isinstance(expected, str):
        raise TypeError(f"expected_status must be int/HTTPStatus/Iterable, got str: {expected!r}")

    if isinstance(expected, (int, HTTPStatus)):
        expected_list = [int(expected)]
    else:
        expected_list = [int(s) for s in expected]

    if response.status_code not in expected_list:
        raise StatusAssertionError(
            actual=response.status_code,
            expected=expected_list,
            url=str(response.request.url),
            body=response.text,
        )


def validate_body(
        response: Response,
        response_model: ResponseModel,
        error_models: dict[int, Type[BaseModel]],
) -> None:
    """
    Валидирует тело ответа.

    Стратегия:
      • Явная response_model — строгая валидация, падает при несоответствии.
        (Используется для 2xx-ответов: форма успеха критична для теста.)
      • 4xx/5xx без response_model — попытка валидации через error_models:
        - модели нет в реестре → пропускаем;
        - модель есть, но не подошла → логируем warning, не падаем
          (форма ошибки — диагностика, не основная проверка теста).
      • 2xx/3xx без response_model — ResponseValidationError
        (пользователь явно попросил валидацию, но модели нет).
    """

    status = response.status_code

    if response_model is not None:
        # Явная модель — строгая валидация для любого статуса
        _validate_strict(response, response_model, status)
        return

    if HTTPStatus.BAD_REQUEST <= status < 600:
        # Ошибочный статус — мягкая валидация через реестр
        model = error_models.get(status)
        if model is None:
            logger.debug(
                "No error model for status %d, skipping response body validation",
                status,
            )
            return
        _validate_soft(response, model, status)
        return

    raise ResponseValidationError(
        f"validate_response=True for status {status}, but no response_model provided. "
        f"Pass response_model to the endpoint or use validate_response=False."
    )


def _validate_strict(response: Response, model: Type[BaseModel], status: int) -> None:
    """Строгая валидация: при любой ошибке поднимает ResponseValidationError."""

    if not response.content:
        return

    try:
        body = response.json()
    except ValueError as exc:
        raise ResponseValidationError(
            f"Expected JSON matching {model.__name__}, got non-JSON: {response.text[:200]}"
        ) from exc

    try:
        model.model_validate(body)
    except ValidationError as exc:
        raise ResponseValidationError(
            f"Response body does not match {model.__name__} "
            f"(status {status}):\n{exc}\n\nBody: {body}"
        ) from exc


def _validate_soft(response: Response, model: Type[BaseModel], status: int) -> None:
    """Мягкая валидация: при ошибке логирует warning и продолжает."""

    if not response.content:
        return

    try:
        body = response.json()
    except ValueError:
        logger.warning(
            "Status %d body is not JSON, cannot validate against %s. Body: %s",
            status, model.__name__, response.text[:200],
        )
        return

    try:
        model.model_validate(body)
    except ValidationError as exc:
        logger.warning(
            "Status %d body does not match registered model %s: %s. Body: %s",
            status, model.__name__, exc, body,
        )


def effective(per_request: Optional[bool], *, default: bool) -> bool:
    return default if per_request is None else per_request
