"""Синхронный клиент проверок и запросов к внешним системам данных (pytest).

  * HTTP-системы (Trino/ClickHouse/Spark) — через ``curl`` (subprocess):
    ``check_http`` (доступность, assert) и ``request`` (-> ``(status_code, body)``).
  * GreenPlum — через ``psycopg2`` (PostgreSQL wire protocol, psql не нужен):
    ``check_greenplum`` выполняет запрос и возвращает строки.
Запросы под конкретные системы (например, Trino ``/v1/statement``) собираются
в самих тестах из ``request``. Изолировано от оркестратора (Airflow).

Использование в тестах::
    client = DataSystemHealthClient()
    client.check_http(TrinoConfig(base_url="http://trino:8080"))
    code, body = client.request(
        TrinoConfig(base_url="http://trino:8080"),
        method="POST", path="/v1/statement", data="SELECT 1",
    )
"""

import logging
import os
import shlex
import subprocess
from typing import List, Mapping, Optional, Tuple

from .config import GreenPlumConfig, HTTPSystemConfig

logger = logging.getLogger("infra.health")


class DataSystemHealthClient:
    """Проверки и запросы к внешним системам через subprocess (curl/psql)."""

    def __init__(
            self,
            curl_bin: str = "curl",
            kinit_bin: str = "kinit",
    ) -> None:
        self._curl_bin = curl_bin
        self._kinit_bin = kinit_bin

    def kinit(self, principal: str, password: str, timeout: float = 30.0) -> None:
        """Получить Kerberos-тикет (``kinit``); пароль подаётся через stdin.

        Вызывать в setup-фикстуре до Kerberos-проверок (``kerberos=True``).
        AssertionError, если тикет получить не удалось.
        """
        try:
            proc = subprocess.run(
                [self._kinit_bin, principal],
                input=password,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except FileNotFoundError:
            assert False, f"Бинарник '{self._kinit_bin}' не найден в PATH"
        except subprocess.TimeoutExpired:
            assert False, f"Таймаут kinit для '{principal}' ({timeout}s)"

        ok = proc.returncode == 0
        logger.info("kinit %s -> %s", principal, "OK" if ok else "FAIL")
        assert ok, (
            f"kinit для '{principal}' не удался: "
            f"{proc.stderr.strip() or proc.stdout.strip() or 'exit ' + str(proc.returncode)}"
        )

    def check_http(self, config: HTTPSystemConfig) -> None:
        """curl к health-эндпоинту; assert на 2xx/3xx (или ``expected_status``)."""
        argv = self._build_curl(config, config.url, capture_body=False)
        logger.info("%s curl: %s", config.name, self._format_command(argv))
        result = self._run(argv, config.timeout)

        code = result.stdout.strip()
        ok = (
                result.returncode == 0
                and code.isdigit()
                and self._status_ok(int(code), config.expected_status)
        )
        logger.info("%s -> %s (HTTP %s)", config.name, "OK" if ok else "FAIL", code or "?")
        assert ok, (
                f"System '{config.name}' недоступна: {config.url} -> HTTP {code or '?'} "
                f"(curl exit {result.returncode})"
                + (f": {result.stderr.strip()}" if result.stderr.strip() else "")
        )

    def request(
            self,
            config: HTTPSystemConfig,
            method: str = "GET",
            path: Optional[str] = None,
            data: Optional[str] = None,
            headers: Optional[Mapping[str, str]] = None,
            expected_status: Tuple[int, ...] = (),
    ) -> Tuple[int, str]:
        """Произвольный HTTP-запрос; вернуть ``(status_code, body)``.

        :param path: путь поверх ``base_url`` (по умолчанию — ``config.url``)
        :param data: тело запроса (для POST/PUT)
        :param headers: доп. заголовки поверх ``config.request_headers()``
        :param expected_status: допустимые коды; пусто -> любой 2xx/3xx
        assert, если код вне ожидаемого диапазона.
        """
        url = config.url if path is None else f"{config.base_url.rstrip('/')}/{path.lstrip('/')}"
        return self._curl(config, url, method, data, headers, expected_status, config.name)

    def check_greenplum(self, config: GreenPlumConfig) -> List[tuple]:
        """Выполнить ``config.query`` в GreenPlum через psycopg2; вернуть строки.

        Подключение по PostgreSQL wire protocol (psql не нужен). По умолчанию
        запрос ``SELECT 1``. AssertionError при ошибке подключения/запроса.
        """
        try:
            import psycopg2
        except ImportError:
            assert False, "psycopg2 не установлен — добавь psycopg2-binary в зависимости"

        logger.info(
            "%s psycopg2: %s@%s:%s/%s query=%r",
            config.name, config.username, config.host, config.port,
            config.database, config.query,
        )
        conn = None
        try:
            conn = psycopg2.connect(
                host=config.host,
                port=config.port,
                dbname=config.database,
                user=config.username,
                password=config.password or None,
                connect_timeout=int(config.timeout),
            )
            with conn.cursor() as cur:
                cur.execute(config.query)
                rows = cur.fetchall() if cur.description else []
        except psycopg2.Error as exc:
            logger.warning("%s -> FAIL", config.name)
            assert False, (
                f"System '{config.name}' недоступна: {config.host}:{config.port} -> "
                f"{str(exc).strip()}"
            )
        finally:
            if conn is not None:
                conn.close()

        logger.info("%s -> OK (%d rows)", config.name, len(rows))
        return rows

    # --------------------------------------------------------------------- #
    # Внутренняя кухня
    # --------------------------------------------------------------------- #
    def _build_curl(
            self,
            config: HTTPSystemConfig,
            url: str,
            method: str = "GET",
            data: Optional[str] = None,
            headers: Optional[Mapping[str, str]] = None,
            capture_body: bool = False,
    ) -> List[str]:
        """Собрать argv для curl. ``capture_body`` -> тело в stdout, иначе только код."""
        argv = [self._curl_bin, "-sS"]
        if capture_body:
            argv += ["-w", "\n%{http_code}"]
        else:
            argv += ["-o", "/dev/null", "-w", "%{http_code}"]
        argv += ["--max-time", str(config.timeout)]

        if not config.verify_tls:
            argv.append("--insecure")
        if config.kerberos:
            argv += ["--negotiate", "-u", ":"]
        elif config.username:
            argv += ["-u", f"{config.username}:{config.password}"]

        if method.upper() != "GET":
            argv += ["-X", method.upper()]

        merged = config.request_headers()
        if headers:
            merged = {**merged, **headers}
        for key, value in merged.items():
            argv += ["-H", f"{key}: {value}"]

        if data is not None:
            argv += ["--data", data]

        argv += list(config.extra_args)
        argv.append(url)
        return argv

    def _curl(
            self,
            config: HTTPSystemConfig,
            url: str,
            method: str,
            data: Optional[str],
            headers: Optional[Mapping[str, str]],
            expected_status: Tuple[int, ...],
            label: str,
    ) -> Tuple[int, str]:
        """Выполнить curl с возвратом тела; assert на статус. -> ``(code, body)``."""
        argv = self._build_curl(config, url, method, data, headers, capture_body=True)
        logger.info("%s curl: %s", label, self._format_command(argv))
        result = self._run(argv, config.timeout)

        body, _, code_str = result.stdout.rpartition("\n")
        code = int(code_str) if code_str.strip().isdigit() else 0
        ok = result.returncode == 0 and self._status_ok(code, expected_status)

        logger.info("%s -> HTTP %s", label, code or "?")
        assert ok, (
                f"Request {method.upper()} {url} -> HTTP {code or '?'} "
                f"(curl exit {result.returncode})"
                + (f": {result.stderr.strip()}" if result.stderr.strip() else "")
        )
        return code, body

    @staticmethod
    def _format_command(argv: List[str]) -> str:
        """Готовая команда строкой; пароль в ``-u user:pass`` маскируется."""
        parts: List[str] = []
        for i, part in enumerate(argv):
            if i > 0 and argv[i - 1] == "-u":
                user, sep, pwd = part.partition(":")
                if sep and pwd:
                    part = f"{user}:***"
            parts.append(shlex.quote(part))
        return " ".join(parts)

    @staticmethod
    def _status_ok(code: int, expected_status: Tuple[int, ...]) -> bool:
        if expected_status:
            return code in expected_status
        return 200 <= code < 400

    def _run(
            self,
            argv: List[str],
            timeout: float,
            env: Optional[Mapping[str, str]] = None,
    ) -> subprocess.CompletedProcess:
        """Запустить команду; assert при отсутствии бинарника или таймауте."""
        run_env = {**os.environ, **env} if env else None
        try:
            return subprocess.run(
                argv, capture_output=True, text=True,
                timeout=timeout + 5, env=run_env,
            )
        except FileNotFoundError:
            assert False, f"Бинарник '{argv[0]}' не найден в PATH"
        except subprocess.TimeoutExpired:
            assert False, f"Таймаут команды '{argv[0]}' ({timeout}s)"
