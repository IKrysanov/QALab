"""Эндпоинты по ресурсам API."""

from .base import BaseEndpoint
from .posts import PostsEndpoint

__all__ = [
    "BaseEndpoint",
    "PostsEndpoint",
]
