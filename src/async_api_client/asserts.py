from typing import Any

import allure
from httpx import Response
from .http_client import StatusCode

from .redirects import RedirectChain


def assert_status_code(response: Response, expected: StatusCode) -> None:
    with allure.step(f"Status code is {expected}"):
        actual = response.status_code
        assert actual == expected, (
            f"Expected {expected}, got {actual}. Body: {response.text}"
        )


def assert_json_has_keys(response: Response, keys: list[str]) -> None:
    with allure.step(f"Response has keys: {keys}"):
        body = response.json()
        missing = [k for k in keys if k not in body]
        assert not missing, f"Missing keys: {missing}. Body: {body}"


def assert_field_equals(obj: Any, field: str, expected: Any) -> None:
    with allure.step(f"Field '{field}' equals {expected!r}"):
        actual = obj.get(field) if isinstance(obj, dict) else getattr(obj, field, None)
        assert actual == expected, f"Field '{field}': expected {expected!r}, got {actual!r}"


def assert_response_time_below(response: Response, ms: float) -> None:
    with allure.step(f"Response time below {ms}ms"):
        elapsed_ms = response.elapsed.total_seconds() * 1000
        assert elapsed_ms < ms, f"Took {elapsed_ms:.1f}ms, expected < {ms}ms"


def get_redirect_chain(response: Response) -> RedirectChain:
    """Достать цепочку редиректов из ответа (всегда есть, может быть пустой)."""
    chain = response.extensions.get("redirects")
    if chain is None:
        return RedirectChain([])
    return chain


def assert_no_redirects(response: Response) -> None:
    chain = get_redirect_chain(response)
    with allure.step("No redirects occurred"):
        assert not chain.has_redirects, (
            f"Expected no redirects, got {chain.count}:\n{chain}"
        )


def assert_redirect_count(response: Response, expected: int) -> None:
    chain = get_redirect_chain(response)
    with allure.step(f"Redirect count is {expected}"):
        assert chain.count == expected, (
            f"Expected {expected} redirects, got {chain.count}:\n{chain}"
        )


def assert_final_url(response: Response, expected_url: str) -> None:
    chain = get_redirect_chain(response)
    with allure.step(f"Final URL is {expected_url}"):
        if not chain.has_redirects:
            actual = str(response.request.url)
        else:
            actual = chain.final_url
        assert actual == expected_url, f"Expected final URL {expected_url!r}, got {actual!r}"


def assert_redirect_status(response: Response, hop_index: int, expected_status: int) -> None:
    """Проверить статус конкретного редирект-хопа (0-indexed)."""

    chain = get_redirect_chain(response)
    with allure.step(f"Redirect hop {hop_index} has status {expected_status}"):
        assert hop_index < chain.count, (
            f"Hop {hop_index} not found, only {chain.count} redirects"
        )
        actual = chain.status_codes[hop_index]
        assert actual == expected_status, (
            f"Hop {hop_index}: expected status {expected_status}, got {actual}"
        )
