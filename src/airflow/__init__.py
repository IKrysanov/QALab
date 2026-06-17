"""Airflow-слой: высокоуровневый клиент поверх async_api_client."""

from .client import AirflowClient

__all__ = ["AirflowClient"]
