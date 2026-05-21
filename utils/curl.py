import shlex
from typing import Iterable, Optional

from httpx import Request

DEFAULT_SENSITIVE_HEADERS = frozenset({
    "authorization",
    "cookie",
    "set-cookie",
})


def to_curl(
        request: Request,
        sensitive_headers: Optional[Iterable[str]] = None,
        mask_value: str = "***",
) -> str:
    """
    Сконвертировать httpx.Request в curl-команду с маскировкой чувствительных заголовков.

    :param request: объект httpx.Request (response.request тоже подходит)
    :param sensitive_headers: имена заголовков для маскирования (case-insensitive).
                              None → использовать DEFAULT_SENSITIVE_HEADERS.
                              Пустой набор → не маскировать ничего.
    :param mask_value: чем заменять значение чувствительного заголовка
    """
    sensitive = (
        DEFAULT_SENSITIVE_HEADERS
        if sensitive_headers is None
        else frozenset(h.lower() for h in sensitive_headers)
    )

    parts: list[str] = ["curl"]

    if request.method.upper() != "GET":
        parts.append(f"-X {request.method.upper()}")

    for name, value in request.headers.items():
        display = mask_value if name.lower() in sensitive else value
        parts.append(f"-H {shlex.quote(f'{name}: {display}')}")

    if request.content:
        try:
            body = request.content.decode("utf-8")
        except UnicodeDecodeError:
            body = f"<binary {len(request.content)} bytes>"
        parts.append(f"--data {shlex.quote(body)}")

    parts.append(shlex.quote(str(request.url)))

    return " ".join(parts)
