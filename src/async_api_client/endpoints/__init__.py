"""Эндпоинты по ресурсам API.

Версионные наборы лежат в подпакетах:
  • ``endpoints.v1`` — Airflow 2.x, Stable REST API ``/api/v1``;
  • ``endpoints.v2`` — Airflow 3.x, REST API ``/api/v2``.
``BaseEndpoint`` общий для обеих версий.
"""

from .base import BaseEndpoint

__all__ = ["BaseEndpoint"]
