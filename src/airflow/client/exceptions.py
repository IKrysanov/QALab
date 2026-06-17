"""Исключения высокоуровневого Airflow-клиента."""


class AirflowClientError(Exception):
    """Базовое исключение клиента."""


class WaitTimeoutError(AirflowClientError, TimeoutError):
    """Объект (DAGRun/TaskInstance) не достиг ожидаемого состояния за отведённое время."""
