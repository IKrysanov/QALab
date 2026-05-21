"""Type aliases для аннотаций HTTP-клиента."""

from http import HTTPStatus
from typing import Iterable, Optional, Type, Union

from pydantic import BaseModel

StatusCode = Union[int, HTTPStatus, Iterable[Union[int, HTTPStatus]], None]

ResponseModel = Optional[Type[BaseModel]]
RequestModel = Optional[Type[BaseModel]]
RequestPayload = Union[BaseModel, dict, None]