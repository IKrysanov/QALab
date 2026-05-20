import logging
from dataclasses import dataclass
from typing import Optional

import allure
from httpx import Response


@dataclass(frozen=True)
class RedirectHop:
    """Один шаг в цепочке редиректов."""

    from_url: str
    to_url: str
    status_code: int
    method: str

    def __str__(self) -> str:
        return f"{self.method} {self.from_url} → [{self.status_code}] → {self.to_url}"


class RedirectChain:
    """Цепочка редиректов с удобными методами для ассертов."""

    def __init__(self, hops: list[RedirectHop]):
        self._hops = hops

    @property
    def hops(self) -> list[RedirectHop]:
        return list(self._hops)

    @property
    def count(self) -> int:
        return len(self._hops)

    @property
    def has_redirects(self) -> bool:
        return bool(self._hops)

    @property
    def final_url(self) -> Optional[str]:
        return self._hops[-1].to_url if self._hops else None

    @property
    def status_codes(self) -> list[int]:
        return [hop.status_code for hop in self._hops]

    def __iter__(self):
        return iter(self._hops)

    def __len__(self) -> int:
        return len(self._hops)

    def __str__(self) -> str:
        if not self._hops:
            return "(no redirects)"
        return "\n".join(str(hop) for hop in self._hops)


class RedirectTracker:
    """
    Адаптер для извлечения и логирования редиректов из httpx.Response.

    Один объект на запрос — извлекает историю, кладёт в логи и allure,
    отдаёт RedirectChain для возможных ассертов в тестах.
    """

    logger = logging.getLogger("async_api_client")

    @classmethod
    def track(cls, response: Response, request_id: str) -> RedirectChain:
        """
        Извлечь цепочку редиректов из ответа и зафиксировать её.

        :param response: финальный httpx.Response (с заполненным response.history)
        :param request_id: идентификатор для корреляции в логах
        :return: RedirectChain — можно передать в тест для ассертов
        """

        chain = cls._build_chain(response)

        if chain.has_redirects:
            cls._log(chain, request_id)
            cls._attach_to_allure(chain)

        return chain

    @staticmethod
    def _build_chain(response: Response) -> RedirectChain:
        hops: list[RedirectHop] = []
        for hop_response in response.history:
            next_url = hop_response.headers.get("location", "")
            hops.append(
                RedirectHop(
                    from_url=str(hop_response.request.url),
                    to_url=next_url,
                    status_code=hop_response.status_code,
                    method=hop_response.request.method,
                )
            )
        return RedirectChain(hops)

    @classmethod
    def _log(cls, chain: RedirectChain, request_id: str) -> None:
        cls.logger.info(
            "↪ [%s] redirects: %d hop(s), final → %s",
            request_id, chain.count, chain.final_url,
        )
        for i, hop in enumerate(chain, 1):
            cls.logger.debug("↪ [%s]   hop %d: %s", request_id, i, hop)

    @staticmethod
    def _attach_to_allure(chain: RedirectChain) -> None:
        payload = "\n".join(f"{i}. {hop}" for i, hop in enumerate(chain, 1))
        allure.attach(
            payload,
            name=f"Redirects ({chain.count})",
            attachment_type=allure.attachment_type.TEXT,
        )
