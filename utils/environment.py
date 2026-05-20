import os
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
DEFAULT_ENV_PATH = BASE_DIR / ".env"


class EnvError(Exception):
    """Ошибка чтения переменной окружения."""


class ConfigEnv:
    """
    Поведение:
      • При создании подгружает .env (если файл существует).
      • Каждый вызов читает актуальное значение из os.environ — без кеша.
      • Типизированные методы валидируют значение и кидают EnvError при несоответствии.
    """

    _TRUE_VALUES = frozenset({"1", "true", "yes", "on", "y", "t"})
    _FALSE_VALUES = frozenset({"0", "false", "no", "off", "n", "f"})

    def __init__(
            self,
            env_path: Optional[Path] = None,
            override: bool = False,
    ):
        """
        :param env_path: путь до .env. По умолчанию — BASE_DIR/.env.
                         Если файл отсутствует — будет использоваться только os.environ.
        :param override: перезаписывать ли уже установленные переменные окружения.
        """

        self._env_path: Path = env_path or DEFAULT_ENV_PATH
        if self._env_path.exists():
            load_dotenv(self._env_path, override=override)

    # --- Базовый геттер ----------------------------------------------------

    def get(
            self,
            key: str,
            default: Any = None,
            required: bool = False,
    ) -> Optional[str]:
        """
        Получить значение переменной окружения как строку.

        :param key: имя переменной
        :param default: значение по умолчанию, если переменной нет
        :param required: если True и переменная отсутствует — кинуть EnvError
        """

        value = os.getenv(key)
        if value is None:
            if required:
                raise EnvError(f"Обязательная переменная окружения '{key}' не найдена")
            return default
        return value

    # --- Типизированные геттеры -------------------------------------------

    def get_int(
            self,
            key: str,
            default: Optional[int] = None,
            required: bool = False,
    ) -> Optional[int]:
        raw = self.get(key, required=required)
        if raw is None:
            return default
        try:
            return int(raw)
        except ValueError as exc:
            raise EnvError(f"ENV '{key}' is not a valid int: {raw!r}") from exc

    def get_float(
            self,
            key: str,
            default: Optional[float] = None,
            required: bool = False,
    ) -> Optional[float]:
        raw = self.get(key, required=required)
        if raw is None:
            return default
        try:
            return float(raw)
        except ValueError as exc:
            raise EnvError(f"ENV '{key}' is not a valid float: {raw!r}") from exc

    def get_bool(
            self,
            key: str,
            default: bool = False,
            required: bool = False,
    ) -> bool:
        raw = self.get(key, required=required)
        if raw is None:
            return default
        normalized = raw.strip().lower()
        if normalized in self._TRUE_VALUES:
            return True
        if normalized in self._FALSE_VALUES:
            return False
        raise EnvError(
            f"ENV '{key}' is not a valid bool: {raw!r}. "
            f"Expected one of {sorted(self._TRUE_VALUES | self._FALSE_VALUES)}"
        )

    def get_list(
            self,
            key: str,
            default: Optional[list[str]] = None,
            required: bool = False,
            separator: str = ",",
    ) -> Optional[list[str]]:
        """Парсит CSV-строку: 'a,b,c' → ['a', 'b', 'c']. Пустые элементы отбрасываются."""
        raw = self.get(key, required=required)
        if raw is None:
            return default if default is not None else []
        return [item.strip() for item in raw.split(separator) if item.strip()]

    # --- Утилиты ----------------------------------------------------------

    def reload(self) -> None:
        """Перечитать .env с override=True."""
        if self._env_path.exists():
            load_dotenv(self._env_path, override=True)

    def __repr__(self) -> str:
        return f"<ConfigEnv env_path={self._env_path}>"
