from typing import Optional, Any
from ..constants import SENSITIVE_HEADERS, SENSITIVE_BODY_KEYS


def mask_headers(headers: dict, mask_sensitive_values: bool = True) -> dict:
    """Маскирует чувствительные значения в headers"""

    sensitive: frozenset[str] = SENSITIVE_HEADERS if mask_sensitive_values else frozenset()
    return {
        k: ("***" if k.lower() in sensitive else v)
        for k, v in (headers or {}).items()
    }


def mask_body(payload: Any) -> Any:
    """Рекурсивно маскирует значения чувствительных ключей в JSON-подобной структуре."""

    if isinstance(payload, dict):
        return {
            k: ("***" if k.lower() in SENSITIVE_BODY_KEYS else mask_body(v))
            for k, v in payload.items()
        }
    if isinstance(payload, list):
        return [mask_body(v) for v in payload]
    return payload


def truncate(text: str, limit: Optional[int] = None) -> str:
    """
    Обрезает message(payload, response_body)
    """
    if limit is None or len(text) <= limit:
        return text
    return f"{text[:limit]}... [truncated, {len(text)} chars total]"
