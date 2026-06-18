"""Синхронный health-check внешних систем данных для pytest.

Использование в тестах::
    client = DataSystemHealthClient()
    client.check_http(TrinoConfig(base_url="http://trino:8080"))
    client.check_greenplum(GreenPlumConfig(host="greenplum", password="secret"))
"""

import logging
import os
import shlex
import subprocess
from typing import List, Mapping, Optional, Union

from .config import GreenPlumConfig, HTTPSystemConfig

logger = logging.getLogger("infra.health")

AnyConfig = Union[HTTPSystemConfig, GreenPlumConfig]


class DataSystemHealthClient:
    """Проверка доступности внешних систем через subprocess (curl/psql)."""

    def __init__(
            self,
            curl_bin: str = "curl",
            psql_bin: str = "psql",
            kinit_bin: str = "kinit",
    ) -> None:
        self._curl_bin = curl_bin
        self._psql_bin = psql_bin
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

    def check(self, config: AnyConfig) -> None:
        """Проверить систему по типу конфига. AssertionError, если недоступна."""
        if isinstance(config, GreenPlumConfig):
            self.check_greenplum(config)
        else:
            self.check_http(config)

    def check_http(self, config: HTTPSystemConfig) -> None:
        """curl к health-эндпоинту; assert на 2xx/3xx (или ``expected_status``)."""
        argv = [
            self._curl_bin, "-sS", "-o", "/dev/null",
            "-w", "%{http_code}", "--max-time", str(config.timeout),
        ]
        if not config.verify_tls:
            argv.append("--insecure")
        if config.kerberos:
            argv += ["--negotiate", "-u", ":"]
        elif config.username:
            argv += ["-u", f"{config.username}:{config.password}"]
        for key, value in config.request_headers().items():
            argv += ["-H", f"{key}: {value}"]
        argv += list(config.extra_args)
        argv.append(config.url)

        logger.info("%s curl: %s", config.name, self._format_command(argv))
        result = self._run(argv, config.timeout)
        code = result.stdout.strip()
        ok = (
            result.returncode == 0
            and code.isdigit()
            and self._status_ok(int(code), config)
        )

        logger.info("%s -> %s (HTTP %s)", config.name, "OK" if ok else "FAIL", code or "?")
        assert ok, (
            f"System '{config.name}' недоступна: {config.url} -> HTTP {code or '?'} "
            f"(curl exit {result.returncode})"
            + (f": {result.stderr.strip()}" if result.stderr.strip() else "")
        )

    def check_greenplum(self, config: GreenPlumConfig) -> None:
        """psql ``SELECT 1``; assert на успешный код возврата."""
        argv = [
            self._psql_bin,
            "-h", config.host, "-p", str(config.port),
            "-U", config.username, "-d", config.database,
            "-w", "-tAc", config.query,
        ]
        env = {"PGCONNECT_TIMEOUT": str(int(config.timeout))}
        if config.password:
            env["PGPASSWORD"] = config.password

        logger.info("%s psql: %s", config.name, self._format_command(argv))
        result = self._run(argv, config.timeout, env=env)
        ok = result.returncode == 0

        logger.info("%s -> %s", config.name, "OK" if ok else "FAIL")
        assert ok, (
            f"System '{config.name}' недоступна: {config.host}:{config.port} -> "
            f"{result.stderr.strip() or 'psql exit ' + str(result.returncode)}"
        )

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
    def _status_ok(code: int, config: HTTPSystemConfig) -> bool:
        if config.expected_status:
            return code in config.expected_status
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
