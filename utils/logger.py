"""
Логирование для тестового проекта.

Использование:
    # один раз при старте (например, в conftest.py)
    from utils.logger import configure_logging
    configure_logging(level="INFO")

    # в любом модуле
    from utils.logger import get_logger
    log = get_logger(__name__)
    log.info("hello")
"""

import json
import logging
import sys
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Mapping, Optional, Union

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOGS_DIR = PROJECT_ROOT / "logs"

MANAGED_LOGGERS = (
    "async_api_client",
    "airflow.client",
    "dags.encryptor",
    "infra.health",
    "s3.client",
    "openshift.client",
    "tests",
    "app",
    "httpx",
    "httpcore",
)

_DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"
_JSON_LOGGERS = ("openshift.client",)

LogLevel = Union[int, str]

_configured: bool = False


class StructuredJsonFormatter(logging.Formatter):
    """JSON Lines formatter для событий, пригодных для AI/CI-парсинга."""

    def format(self, record: logging.LogRecord) -> str:
        event_data = getattr(record, "event_data", None)
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=timezone.utc,
            ).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
        }
        if isinstance(event_data, Mapping):
            payload.update(
                {
                    key: value
                    for key, value in event_data.items()
                    if key not in payload
                }
            )
        else:
            payload["message"] = record.getMessage()

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )


class RoutingFormatter(logging.Formatter):
    """Выбирает JSON для структурированных клиентов и text для остальных."""

    def __init__(
            self,
            text_format: str,
            datefmt: str,
    ) -> None:
        super().__init__()
        self._text_formatter = logging.Formatter(
            text_format,
            datefmt=datefmt,
        )
        self._json_formatter = StructuredJsonFormatter()

    def format(self, record: logging.LogRecord) -> str:
        if any(
                record.name == name
                or record.name.startswith(f"{name}.")
                for name in _JSON_LOGGERS
        ):
            return self._json_formatter.format(record)
        return self._text_formatter.format(record)


def configure_logging(
        level: LogLevel = logging.INFO,
        log_file: Optional[str] = "tests_cycle",
        logs_dir: Optional[Path] = DEFAULT_LOGS_DIR,
        use_console: bool = True,
        fmt: str = _DEFAULT_FORMAT,
        datefmt: str = _DEFAULT_DATEFMT,
        backup_count: int = 7,
        force: bool = False,
) -> None:
    """
    Настроить корневое логирование один раз за процесс.

    :param level: уровень логирования (int или строка вроде "DEBUG", "INFO")
    :param log_file: базовое имя файла без расширения; None — не писать в файл
    :param logs_dir: каталог для логов; None — не писать в файл
    :param use_console: писать ли в stdout
    :param fmt: формат сообщения
    :param datefmt: формат даты
    :param backup_count: сколько суточных файлов хранить (TimedRotatingFileHandler)
    :param force: переконфигурировать, даже если уже настроено
    """
    global _configured
    if _configured and not force:
        return

    formatter = RoutingFormatter(fmt, datefmt)
    handlers: list[logging.Handler] = []

    if use_console:
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(formatter)
        handlers.append(console)

    if log_file and logs_dir:
        logs_dir = Path(logs_dir)
        try:
            logs_dir.mkdir(parents=True, exist_ok=True)
            file_path = logs_dir / f"{log_file}.log"
            file_handler = TimedRotatingFileHandler(
                filename=file_path,
                when="midnight",
                interval=1,
                backupCount=backup_count,
                encoding="utf-8",
                utc=False,
            )
            file_handler.setFormatter(formatter)
            handlers.append(file_handler)
        except OSError as exc:
            print(
                f"[logger] не удалось создать файловый обработчик в {logs_dir}: {exc}",
                file=sys.stderr,
            )

    for name in MANAGED_LOGGERS:
        target = logging.getLogger(name)
        target.setLevel(level)
        target.propagate = False

        for old in list(target.handlers):
            target.removeHandler(old)
        for handler in handlers:
            target.addHandler(handler)

    _configured = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    if not _configured:
        configure_logging()

    if name is None:
        name = "app"
    return logging.getLogger(name)


def log_event(
        logger: logging.Logger,
        level: int,
        event: str,
        **fields: Any,
) -> None:
    """Записать структурированное событие без конкатенации key=value."""

    event_data = {"event": event, **fields}
    logger.log(
        level,
        event,
        extra={"event_data": event_data},
    )


def set_level(level: LogLevel, logger_name: Optional[str] = None) -> None:
    """
    Поменять уровень логирования на лету.

    :param level: новый уровень
    :param logger_name: имя логгера; None — применить ко всем managed-логгерам
    """
    if logger_name is None:
        for name in MANAGED_LOGGERS:
            logging.getLogger(name).setLevel(level)
    else:
        logging.getLogger(logger_name).setLevel(level)
