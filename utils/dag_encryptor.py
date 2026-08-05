"""Fernet-шифрование локальных DAG-файлов перед загрузкой в Ozone S3.

Читает DAG-и из локальной папки рядом с тестами и отдаёт зашифрованное
содержимое байтами — ровно в том виде, в каком его ждёт ``S3Client.upload_bytes``.

Использование::

    from utils.dag_encryptor import DagEncryptor

    encryptor = DagEncryptor.from_env()          # ключ из DAG_FERNET_KEY
    for dag in encryptor.encrypt_dir():          # все *.py из tests/dags
        s3_client.upload_bytes(dag.data, dag.object_key("dags"))

Ключ никогда не пишется в логи и не попадает в тексты исключений. Сгенерировать
новый можно так::

    python -c "from utils.dag_encryptor import DagEncryptor; print(DagEncryptor.generate_key())"
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Union

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from utils.environment import ConfigEnv
from utils.logger import get_logger

PathLike = Union[str, Path]
KeyMaterial = Union[str, bytes]
KeyOrKeys = Union[KeyMaterial, Sequence[KeyMaterial]]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DAGS_DIR = PROJECT_ROOT / "tests" / "dags"
DEFAULT_PATTERN = "*.py"
DEFAULT_KEY_ENV = "DAG_FERNET_KEY"
DEFAULT_DIR_ENV = "DAGS_LOCAL_DIR"

logger = get_logger("dags.encryptor")

__all__ = [
    "DagEncryptor",
    "EncryptedDag",
    "DagEncryptionError",
    "DagKeyError",
    "DagDecryptionError",
    "DEFAULT_DAGS_DIR",
    "DEFAULT_KEY_ENV",
]


class DagEncryptionError(RuntimeError):
    """Базовая ошибка шифратора DAG-файлов."""


class DagKeyError(DagEncryptionError, ValueError):
    """Ключ Fernet отсутствует или имеет неверный формат."""


class DagDecryptionError(DagEncryptionError):
    """Токен не расшифровывается текущим набором ключей."""


@dataclass(frozen=True)
class EncryptedDag:
    """Зашифрованное содержимое одного DAG-файла."""

    source: Path
    relative_path: str
    data: bytes
    plain_size: int

    @property
    def name(self) -> str:
        """Имя исходного файла, например ``my_dag.py``."""
        return self.source.name

    @property
    def size(self) -> int:
        """Размер зашифрованного содержимого в байтах."""
        return len(self.data)

    def object_key(self, prefix: str = "") -> str:
        """Ключ объекта в бакете: ``prefix`` + путь относительно папки DAG-ов.

        Вложенность сохраняется, так что при ``recursive=True`` структура папок
        воспроизводится в бакете как есть.
        """
        cleaned = prefix.strip("/")
        return f"{cleaned}/{self.relative_path}" if cleaned else self.relative_path


class DagEncryptor:
    """Шифрует локальные DAG-файлы через Fernet (симметричный AES-128-CBC + HMAC).

    Принимает один ключ или несколько: шифрование всегда идёт первым ключом,
    расшифровка пробует все по очереди (``MultiFernet``) — это позволяет
    переживать ротацию ключа, не переливая уже загруженные объекты.
    """

    def __init__(
            self,
            key: KeyOrKeys,
            *,
            dags_dir: Optional[PathLike] = None,
            pattern: str = DEFAULT_PATTERN,
            recursive: bool = False,
    ) -> None:
        """
        :param key: ключ Fernet (str/bytes) либо последовательность ключей для ротации
        :param dags_dir: папка с DAG-ами; по умолчанию ``tests/dags`` в корне проекта
        :param pattern: glob-маска отбираемых файлов
        :param recursive: искать ли во вложенных папках
        """
        self._fernet, self._key_count = _build_fernet(key)
        self._dags_dir = Path(dags_dir) if dags_dir is not None else DEFAULT_DAGS_DIR
        self._pattern = pattern
        self._recursive = recursive

    @classmethod
    def from_env(
            cls,
            key_var: str = DEFAULT_KEY_ENV,
            *,
            env: Optional[ConfigEnv] = None,
            dags_dir: Optional[PathLike] = None,
            pattern: str = DEFAULT_PATTERN,
            recursive: bool = False,
    ) -> "DagEncryptor":
        """Собрать шифратор из окружения.

        Ключ читается из ``key_var`` (по умолчанию ``DAG_FERNET_KEY``); несколько
        ключей для ротации перечисляются через запятую. Папка с DAG-ами берётся из
        аргумента, иначе из ``DAGS_LOCAL_DIR``, иначе — дефолтная.
        """
        config = env or ConfigEnv()
        keys = config.get_list(key_var, required=True) or []
        directory = dags_dir or config.get(DEFAULT_DIR_ENV)
        return cls(keys, dags_dir=directory, pattern=pattern, recursive=recursive)

    @staticmethod
    def generate_key() -> str:
        """Сгенерировать новый ключ Fernet (32 url-safe base64 байта)."""
        return Fernet.generate_key().decode("ascii")

    @property
    def dags_dir(self) -> Path:
        """Папка, из которой берутся DAG-файлы."""
        return self._dags_dir

    # ------------------------------------------------------------------ #
    #  Сырые данные                                                        #
    # ------------------------------------------------------------------ #

    def encrypt(self, data: bytes) -> bytes:
        """Зашифровать байты и вернуть Fernet-токен."""
        return self._fernet.encrypt(data)

    def decrypt(self, token: bytes, *, ttl: Optional[int] = None) -> bytes:
        """Расшифровать Fernet-токен.

        ``ttl`` — максимальный возраст токена в секундах (Fernet хранит в токене
        метку времени); по умолчанию возраст не проверяется.
        Бросает :class:`DagDecryptionError`, если токен повреждён, подделан или
        зашифрован ключом, которого нет в наборе.
        """
        try:
            return self._fernet.decrypt(token, ttl=ttl)
        except InvalidToken as exc:
            raise DagDecryptionError(
                "Failed to decrypt payload: token is malformed, expired "
                "or was encrypted with a key outside the current key set"
            ) from exc

    def encrypt_text(self, text: str, *, encoding: str = "utf-8") -> bytes:
        """Зашифровать строку."""
        return self.encrypt(text.encode(encoding))

    def decrypt_text(
            self,
            token: bytes,
            *,
            encoding: str = "utf-8",
            ttl: Optional[int] = None,
    ) -> str:
        """Расшифровать токен и декодировать в строку."""
        return self.decrypt(token, ttl=ttl).decode(encoding)

    # ------------------------------------------------------------------ #
    #  Файлы и папки                                                       #
    # ------------------------------------------------------------------ #

    def list_files(
            self,
            directory: Optional[PathLike] = None,
            *,
            pattern: Optional[str] = None,
            recursive: Optional[bool] = None,
    ) -> List[Path]:
        """Найти DAG-файлы, которые попадут под шифрование (отсортированы по пути).

        Бросает :class:`FileNotFoundError`/:class:`NotADirectoryError`, если папки
        нет или это не папка — иначе опечатка в пути молча превратилась бы
        в «ноль DAG-ов».
        """
        target = Path(directory) if directory is not None else self._dags_dir
        if not target.exists():
            raise FileNotFoundError(f"DAGs directory does not exist: {target}")
        if not target.is_dir():
            raise NotADirectoryError(f"DAGs path is not a directory: {target}")

        glob_pattern = pattern if pattern is not None else self._pattern
        deep = self._recursive if recursive is None else recursive
        walk = target.rglob if deep else target.glob
        return sorted(path for path in walk(glob_pattern) if path.is_file())

    def encrypt_file(self, path: PathLike) -> EncryptedDag:
        """Зашифровать один DAG-файл.

        Путь может быть абсолютным или относительным — относительный
        разрешается от папки DAG-ов.
        """
        source = self._resolve(path)
        if not source.is_file():
            raise FileNotFoundError(f"DAG file does not exist: {source}")

        plain = source.read_bytes()
        item = EncryptedDag(
            source=source,
            relative_path=self._relative_path(source),
            data=self.encrypt(plain),
            plain_size=len(plain),
        )
        logger.debug(
            "event=dag_encrypted source=%s plain_bytes=%d token_bytes=%d",
            item.relative_path,
            item.plain_size,
            item.size,
        )
        return item

    def encrypt_dir(
            self,
            directory: Optional[PathLike] = None,
            *,
            pattern: Optional[str] = None,
            recursive: Optional[bool] = None,
            allow_empty: bool = False,
    ) -> List[EncryptedDag]:
        """Зашифровать все подходящие DAG-файлы папки.

        При ``allow_empty=False`` (по умолчанию) пустая выборка — это ошибка:
        в тестах «не нашлось ни одного DAG-а» почти всегда означает неверный путь
        или маску, а не намерение загрузить пустоту.
        """
        files = self.list_files(directory, pattern=pattern, recursive=recursive)
        target = Path(directory) if directory is not None else self._dags_dir
        if not files and not allow_empty:
            raise FileNotFoundError(
                f"No DAG files matched '{pattern or self._pattern}' in {target}"
            )

        items = [self.encrypt_file(path) for path in files]
        logger.info(
            "event=dags_encrypted dir=%s files=%d plain_bytes=%d token_bytes=%d",
            target,
            len(items),
            sum(item.plain_size for item in items),
            sum(item.size for item in items),
        )
        return items

    def encrypt_to_file(self, path: PathLike, destination: PathLike) -> Path:
        """Зашифровать DAG-файл и записать токен на диск.

        Нужно, когда загрузка идёт через ``S3Client.upload_file`` (по пути,
        а не по байтам). Недостающие родительские папки создаются.
        """
        item = self.encrypt_file(path)
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(item.data)
        logger.debug(
            "event=dag_encrypted_to_file source=%s destination=%s token_bytes=%d",
            item.relative_path,
            target,
            item.size,
        )
        return target

    def decrypt_file(self, path: PathLike, *, ttl: Optional[int] = None) -> bytes:
        """Прочитать файл с токеном и расшифровать его содержимое."""
        source = Path(path)
        if not source.is_file():
            raise FileNotFoundError(f"Encrypted file does not exist: {source}")
        return self.decrypt(source.read_bytes(), ttl=ttl)

    # ------------------------------------------------------------------ #
    #  Внутреннее                                                          #
    # ------------------------------------------------------------------ #

    def _resolve(self, path: PathLike) -> Path:
        """Относительный путь — от папки DAG-ов, абсолютный — как есть."""
        candidate = Path(path)
        return candidate if candidate.is_absolute() else self._dags_dir / candidate

    def _relative_path(self, source: Path) -> str:
        """Путь относительно папки DAG-ов в posix-виде; вне папки — только имя файла."""
        try:
            return source.resolve().relative_to(self._dags_dir.resolve()).as_posix()
        except ValueError:
            return source.name

    def __repr__(self) -> str:
        # Ключи наружу не отдаём — только их количество.
        return (
            f"<DagEncryptor dags_dir={self._dags_dir} pattern={self._pattern!r} "
            f"recursive={self._recursive} keys={self._key_count}>"
        )


def _build_fernet(key: KeyOrKeys) -> tuple[MultiFernet, int]:
    """Собрать ``MultiFernet`` из одного ключа или их последовательности.

    Материал ключа не попадает ни в сообщение об ошибке, ни в цепочку исключений
    (``from None``) — иначе секрет утёк бы в отчёт CI при первой же опечатке.
    """
    raw_keys: Sequence[KeyMaterial] = (
        [key] if isinstance(key, (str, bytes)) else list(key)
    )
    if not raw_keys:
        raise DagKeyError(
            f"At least one Fernet key is required "
            f"(set {DEFAULT_KEY_ENV} or pass it explicitly)"
        )

    fernets = []
    for index, raw in enumerate(raw_keys):
        material = raw.encode("ascii") if isinstance(raw, str) else raw
        try:
            fernets.append(Fernet(material.strip()))
        except (ValueError, TypeError) as exc:
            raise DagKeyError(
                f"Key #{index} is not a valid Fernet key: expected 32 url-safe "
                f"base64-encoded bytes ({type(exc).__name__}). "
                f"Generate one with DagEncryptor.generate_key()"
            ) from None

    return MultiFernet(fernets), len(fernets)
