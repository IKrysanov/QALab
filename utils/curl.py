import shlex
from typing import Iterable

from httpx import Request


SENSITIVE_HEADERS = ("authorization", "x-api-key", "cookie", "x-auth-token", "set-cookie", "proxy-authorization")


def to_curl(
    request: Request,
    mask_sensitive: bool = True,
    sensitive_headers: Iterable[str] = SENSITIVE_HEADERS,
) -> str:
    """
    Сконвертировать httpx.Request в curl-команду.

    :param request: объект httpx.Request (response.request тоже подходит)
    :param mask_sensitive: маскировать значения чувствительных заголовков
    :param sensitive_headers: имена заголовков для маскирования (lower-case)
    """

    parts: list[str] = ["curl"]

    # Метод
    if request.method.upper() != "GET":
        parts.append(f"-X {request.method.upper()}")

    # Заголовки
    sensitive = {h.lower() for h in sensitive_headers}
    for name, value in request.headers.items():
        display_value = "***" if mask_sensitive and name.lower() in sensitive else value
        parts.append(f"-H {shlex.quote(f'{name}: {display_value}')}")

    # Тело — у httpx это байты в .content
    if request.content:
        try:
            body = request.content.decode("utf-8")
        except UnicodeDecodeError:
            body = f"<binary {len(request.content)} bytes>"
        parts.append(f"--data {shlex.quote(body)}")

    # URL — в самом конце, как принято
    parts.append(shlex.quote(str(request.url)))

    return " ".join(parts)