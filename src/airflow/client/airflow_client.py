"""Высокоуровневый асинхронный клиент Airflow для DAG-тестов.

Обёртка над :class:`AsyncAPIClient` (Airflow Stable REST API ``/api/v1``).
Скрывает работу с сырыми ``httpx.Response`` и отдаёт распарсенные pydantic-модели,
а также предоставляет polling-хелперы (``trigger_and_wait``, ``wait_for_dag_run`` и т.п.)
для типичных сценариев: запустить DAG, дождаться завершения, проверить состояния
тасок, забрать XCom/логи.

Аутентификация сюда НЕ добавляется — она настраивается снаружи (см. ``auth.py``)
и передаётся в :class:`AsyncAPIClient`.
"""

from __future__ import annotations

import asyncio
import logging
import time
from http import HTTPStatus
from typing import Any, List, Optional, Sequence, Type, TypeVar

import allure
from pydantic import BaseModel

from src.async_api_client.client import AsyncAPIClient
from src.async_api_client.config import APIConfig
from src.async_api_client.auth import AsyncAuthStrategy
from src.async_api_client.models.v1.dag_runs import (
    DAGRunCollectionResponse,
    DAGRunResponse,
    DAGRunPatchBody,
    SetDagRunNoteBody,
    TriggerDAGRunPostBody,
)
from src.async_api_client.models.v1.task_instances import (
    SetTaskInstanceNoteBody,
    TaskInstanceCollectionResponse,
    TaskInstanceResponse,
    TaskInstancesLogResponse,
)
from src.async_api_client.models.v1.xcoms import XComResponse
from src.async_api_client.models.v1.dags import (
    DAGCollectionResponse,
    DAGPatchBody,
    DAGResponse,
)
from src.async_api_client.models.v1.connections import (
    ConnectionBody,
    ConnectionCollectionItem,
    ConnectionResponse,
    ConnectionCollectionResponse,
    ConnectionTestResponse,
)
from src.async_api_client.models.v1.variables import (
    VariableBody,
    VariableCollectionItem,
    VariableCollectionResponse,
    VariableResponse,
)
from src.async_api_client.models.v1.pools import (
    PoolBody,
    PoolCollectionResponse,
    PoolResponse,
)
from src.async_api_client.models.v1.monitor import (
    HealthInfoResponse,
    VersionInfo,
)

from .exceptions import AirflowClientError, WaitTimeoutError
from .states import TERMINAL_DAG_RUN_STATES, TERMINAL_TASK_INSTANCE_STATES

M = TypeVar("M", bound=BaseModel)

# Высокоуровневый логгер: лайфцикл и мутации — на INFO, детали поллинга — на DEBUG.
# Сырые HTTP запрос/ответ уже логирует транспорт (logger "async_api_client"),
# поэтому здесь read-операции (get/list) намеренно не логируются — чтобы не дублировать.
logger = logging.getLogger("airflow.client")

DEFAULT_WAIT_TIMEOUT = 300.0
DEFAULT_POLL_INTERVAL = 2.0


class AirflowClient:
    """Обёртка над ``AsyncAPIClient`` для тестов DAG-ов.

    Использование::

        async with AirflowClient.from_config(config, auth=auth, session=session) as af:
            run = await af.trigger_and_wait("my_dag", conf={"x": 1})
            assert run.state == "success"
            tis = await af.list_task_instances("my_dag", run.dag_run_id)

    Или поверх уже созданного клиента (управление его жизненным циклом — на вызывающем)::

        af = AirflowClient(existing_api_client)
    """

    def __init__(self, api: AsyncAPIClient, *, owns_api: bool = False):
        self._api = api
        self._owns_api = owns_api

    @classmethod
    def from_config(
            cls,
            config: APIConfig,
            *,
            auth: Optional[AsyncAuthStrategy] = None,
            **kwargs: Any,
    ) -> "AirflowClient":
        """Собрать клиент из конфига. Созданный ``AsyncAPIClient`` закрывается в ``aclose``.

        ``auth``/``session`` и пр. пробрасываются в ``AsyncAPIClient`` как есть —
        логику аутентификации клиент не трогает.
        """
        api = AsyncAPIClient(config, auth=auth, **kwargs)
        return cls(api, owns_api=True)

    @property
    def api(self) -> AsyncAPIClient:
        """Доступ к низкоуровневому клиенту для нестандартных вызовов."""
        return self._api

    async def __aenter__(self) -> "AirflowClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Закрыть низкоуровневый клиент, если он создан этим объектом."""
        if self._owns_api:
            await self._api.aclose()

    # ------------------------------------------------------------------ #
    #  DAG runs                                                            #
    # ------------------------------------------------------------------ #

    async def trigger_dag(
            self,
            dag_id: str,
            *,
            conf: Optional[dict] = None,
            dag_run_id: Optional[str] = None,
            logical_date: Optional[str] = None,
            data_interval_start: Optional[str] = None,
            data_interval_end: Optional[str] = None,
            note: Optional[str] = None,
    ) -> DAGRunResponse:
        """Запустить DAG (POST /dags/{dag_id}/dagRuns) и вернуть созданный DAGRun."""
        body = TriggerDAGRunPostBody(
            dag_run_id=dag_run_id,
            logical_date=logical_date,
            data_interval_start=data_interval_start,
            data_interval_end=data_interval_end,
            conf=conf,
            note=note,
        )
        with allure.step(f"Trigger DAG '{dag_id}'"):
            resp = await self._api.dag_runs.trigger(dag_id, body)
        run = _parse(resp, DAGRunResponse)
        logger.info("Triggered DAG '%s' (run_id=%s, state=%s)", dag_id, run.dag_run_id, run.state)
        return run

    async def get_dag_run(self, dag_id: str, dag_run_id: str) -> DAGRunResponse:
        """GET /dags/{dag_id}/dagRuns/{dag_run_id}."""
        resp = await self._api.dag_runs.get(dag_id, dag_run_id)
        return _parse(resp, DAGRunResponse)

    async def list_dag_runs(self, dag_id: str, **kwargs: Any) -> List[DAGRunResponse]:
        """Список DAGRun-ов для DAG (одна страница; фильтры пробрасываются в endpoint)."""
        resp = await self._api.dag_runs.list(dag_id, **kwargs)
        return _parse(resp, DAGRunCollectionResponse).dag_runs

    async def get_all_dag_runs(
            self,
            dag_id: str,
            *,
            batch_size: int = 100,
            **kwargs: Any,
    ) -> List[DAGRunResponse]:
        """Получить ВСЕ DAGRun-ы DAG-а, проходя пагинацию.

        ``limit``/``offset`` управляются автоматически (страница — ``batch_size``);
        остальные фильтры (``state``/``execution_date_lte``/``order_by``/...) пробрасываются
        в endpoint и применяются на стороне Airflow.
        """
        runs: List[DAGRunResponse] = []
        offset = 0
        while True:
            page = await self.list_dag_runs(
                dag_id, limit=batch_size, offset=offset, **kwargs,
            )
            runs.extend(page)
            if len(page) < batch_size:
                break
            offset += batch_size
        return runs

    async def wait_for_dag_run(
            self,
            dag_id: str,
            dag_run_id: str,
            *,
            timeout: float = DEFAULT_WAIT_TIMEOUT,
            poll_interval: float = DEFAULT_POLL_INTERVAL,
            target_states: Optional[Sequence[str]] = None,
    ) -> DAGRunResponse:
        """Поллить DAGRun, пока он не достигнет финального состояния.

        По умолчанию ждём любое терминальное состояние (success/failed) и
        возвращаем его — проверку конкретного состояния делает вызывающий тест.
        Если задан ``target_states`` — останавливаемся также при попадании в него
        (полезно, например, чтобы дождаться промежуточного ``running``).
        Бросает :class:`WaitTimeoutError`, если состояние не достигнуто за ``timeout``.
        """
        stop_states = set(TERMINAL_DAG_RUN_STATES)
        if target_states:
            stop_states |= set(target_states)

        with allure.step(f"Wait for DAG run '{dag_id}/{dag_run_id}' -> {sorted(stop_states)}"):
            run = await self._poll(
                lambda: self.get_dag_run(dag_id, dag_run_id),
                lambda r: r.state in stop_states,
                timeout=timeout,
                poll_interval=poll_interval,
                label=f"DAG run '{dag_id}/{dag_run_id}'",
            )
        if run is None:
            last = await self.get_dag_run(dag_id, dag_run_id)
            logger.error(
                "DAG run '%s/%s' did not reach %s within %ss (last state: %r)",
                dag_id, dag_run_id, sorted(stop_states), timeout, last.state,
            )
            raise WaitTimeoutError(
                f"DAG run '{dag_id}/{dag_run_id}' did not reach {sorted(stop_states)} "
                f"within {timeout}s (last state: {last.state!r})"
            )
        if run.state == "failed":
            logger.warning("DAG run '%s/%s' finished in state %r", dag_id, dag_run_id, run.state)
        else:
            logger.info("DAG run '%s/%s' reached state %r", dag_id, dag_run_id, run.state)
        return run

    async def trigger_and_wait(
            self,
            dag_id: str,
            *,
            conf: Optional[dict] = None,
            dag_run_id: Optional[str] = None,
            logical_date: Optional[str] = None,
            note: Optional[str] = None,
            timeout: float = DEFAULT_WAIT_TIMEOUT,
            poll_interval: float = DEFAULT_POLL_INTERVAL,
            target_states: Optional[Sequence[str]] = None,
    ) -> DAGRunResponse:
        """Запустить DAG и дождаться его финального состояния."""
        run = await self.trigger_dag(
            dag_id,
            conf=conf,
            dag_run_id=dag_run_id,
            logical_date=logical_date,
            note=note,
        )
        return await self.wait_for_dag_run(
            dag_id,
            run.dag_run_id,
            timeout=timeout,
            poll_interval=poll_interval,
            target_states=target_states,
        )

    async def set_dag_run_state(
            self, dag_id: str, dag_run_id: str, state: str,
    ) -> DAGRunResponse:
        """PATCH состояния DAGRun (success/failed/queued)."""
        resp = await self._api.dag_runs.patch(dag_id, dag_run_id, DAGRunPatchBody(state=state))
        logger.info("Set DAG run '%s/%s' state -> %s", dag_id, dag_run_id, state)
        return _parse(resp, DAGRunResponse)

    async def set_dag_run_note(
            self, dag_id: str, dag_run_id: str, note: str,
    ) -> DAGRunResponse:
        """Установить note на DAGRun."""
        resp = await self._api.dag_runs.set_note(dag_id, dag_run_id, SetDagRunNoteBody(note=note))
        logger.debug("Set note on DAG run '%s/%s'", dag_id, dag_run_id)
        return _parse(resp, DAGRunResponse)

    async def cleanup_old_dag_runs(
            self,
            dag_id: str,
            *,
            older_than: Optional[str] = None,
            keep_last: Optional[int] = None,
            states: Optional[Sequence[str]] = None,
            batch_size: int = 100,
            dry_run: bool = False,
    ) -> List[str]:
        """Удалить старые DAGRun-ы у DAG-а; вернуть id удалённых прогонов.

        «Старый» задаётся хотя бы одним критерием (можно комбинировать):
          * ``older_than`` — ISO-дата; удаляются прогоны с ``execution_date`` <= неё
            (фильтр ``execution_date_lte`` на стороне API);
          * ``keep_last`` — оставить ``keep_last`` самых свежих прогонов, остальные удалить.
        ``states`` ограничивает удаление прогонами в указанных состояниях.
        ``dry_run=True`` ничего не удаляет — только возвращает id кандидатов.

        Бросает :class:`ValueError`, если не задан ни ``older_than``, ни ``keep_last``
        (защита от случайного сноса всех прогонов DAG-а).
        """
        if older_than is None and keep_last is None:
            raise ValueError(
                "cleanup_old_dag_runs requires 'older_than' or 'keep_last' "
                "(refusing to delete all dag runs)"
            )

        # Свежие — первыми (keep_last отрезает «голову», удаляется «хвост»).
        runs = await self.get_all_dag_runs(
            dag_id,
            execution_date_lte=older_than,
            state=list(states) if states else None,
            order_by="-execution_date",
            batch_size=batch_size,
        )

        to_delete = runs[keep_last:] if keep_last is not None else runs
        deleted: List[str] = []

        with allure.step(
                f"Cleanup dag runs of '{dag_id}' "
                f"({'dry-run, ' if dry_run else ''}{len(to_delete)} of {len(runs)})"
        ):
            for run in to_delete:
                if not dry_run:
                    await self._api.dag_runs.delete(dag_id, run.dag_run_id)
                deleted.append(run.dag_run_id)
                logger.debug(
                    "%s dag run '%s/%s'",
                    "Would delete" if dry_run else "Deleted", dag_id, run.dag_run_id,
                )

        logger.info(
            "Cleanup '%s': %s %d dag run(s) (kept %d, scanned %d)",
            dag_id, "would delete" if dry_run else "deleted",
            len(deleted), len(runs) - len(deleted), len(runs),
        )
        return deleted

    # ------------------------------------------------------------------ #
    #  Task instances                                                      #
    # ------------------------------------------------------------------ #

    async def get_task_instance(
            self, dag_id: str, dag_run_id: str, task_id: str,
    ) -> TaskInstanceResponse:
        """GET одной таски в рамках DAGRun."""
        resp = await self._api.task_instances.get(dag_id, dag_run_id, task_id)
        return _parse(resp, TaskInstanceResponse)

    async def list_task_instances(
            self, dag_id: str, dag_run_id: str, **kwargs: Any,
    ) -> List[TaskInstanceResponse]:
        """Список тасок DAGRun (фильтры — state/pool/queue/... — пробрасываются)."""
        resp = await self._api.task_instances.list(dag_id, dag_run_id, **kwargs)
        return _parse(resp, TaskInstanceCollectionResponse).task_instances

    async def wait_for_task_instance(
            self,
            dag_id: str,
            dag_run_id: str,
            task_id: str,
            *,
            timeout: float = DEFAULT_WAIT_TIMEOUT,
            poll_interval: float = DEFAULT_POLL_INTERVAL,
            target_states: Optional[Sequence[str]] = None,
    ) -> TaskInstanceResponse:
        """Поллить таску, пока она не достигнет финального состояния.

        По умолчанию ждём любое терминальное состояние таски; ``target_states``
        расширяет набор останавливающих состояний.
        """
        stop_states = set(TERMINAL_TASK_INSTANCE_STATES)
        if target_states:
            stop_states |= set(target_states)

        with allure.step(f"Wait for task '{dag_id}/{dag_run_id}/{task_id}' -> {sorted(stop_states)}"):
            ti = await self._poll(
                lambda: self.get_task_instance(dag_id, dag_run_id, task_id),
                lambda t: t.state in stop_states,
                timeout=timeout,
                poll_interval=poll_interval,
                label=f"task '{dag_id}/{dag_run_id}/{task_id}'",
            )
        if ti is None:
            last = await self.get_task_instance(dag_id, dag_run_id, task_id)
            logger.error(
                "Task '%s/%s/%s' did not reach %s within %ss (last state: %r)",
                dag_id, dag_run_id, task_id, sorted(stop_states), timeout, last.state,
            )
            raise WaitTimeoutError(
                f"Task '{dag_id}/{dag_run_id}/{task_id}' did not reach {sorted(stop_states)} "
                f"within {timeout}s (last state: {last.state!r})"
            )
        if ti.state in ("failed", "upstream_failed"):
            logger.warning("Task '%s/%s/%s' finished in state %r", dag_id, dag_run_id, task_id, ti.state)
        else:
            logger.info("Task '%s/%s/%s' reached state %r", dag_id, dag_run_id, task_id, ti.state)
        return ti

    async def set_task_instance_note(
            self,
            dag_id: str,
            dag_run_id: str,
            task_id: str,
            note: str,
            *,
            map_index: Optional[int] = None,
    ) -> TaskInstanceResponse:
        """Установить note на таску."""
        resp = await self._api.task_instances.set_note(
            dag_id, dag_run_id, task_id, SetTaskInstanceNoteBody(note=note), map_index=map_index,
        )
        logger.debug("Set note on task '%s/%s/%s'", dag_id, dag_run_id, task_id)
        return _parse(resp, TaskInstanceResponse)

    # ------------------------------------------------------------------ #
    #  Logs / XCom                                                         #
    # ------------------------------------------------------------------ #

    async def get_task_log(
            self,
            dag_id: str,
            dag_run_id: str,
            task_id: str,
            *,
            try_number: Optional[int] = None,
            full_content: bool = True,
            map_index: Optional[int] = None,
    ) -> Any:
        """Лог таски за попытку ``try_number`` (по умолчанию — последняя попытка).

        Возвращает поле ``content`` ответа (текст/структура — как отдал Airflow).
        """
        if try_number is None:
            ti = await self.get_task_instance(dag_id, dag_run_id, task_id)
            try_number = ti.try_number or 1
        resp = await self._api.task_instances.get_log(
            dag_id, dag_run_id, task_id, try_number,
            full_content=full_content, map_index=map_index,
        )
        return _parse(resp, TaskInstancesLogResponse).content

    async def get_xcom(
            self,
            dag_id: str,
            dag_run_id: str,
            task_id: str,
            key: str = "return_value",
            *,
            map_index: Optional[int] = None,
            deserialize: Optional[bool] = None,
            stringify: Optional[bool] = None,
    ) -> Any:
        """Вернуть значение XCom-записи (поле ``value``)."""
        resp = await self._api.task_instances.get_xcom_entry(
            dag_id, dag_run_id, task_id, key,
            map_index=map_index, deserialize=deserialize, stringify=stringify,
        )
        return _parse(resp, XComResponse).value

    # ------------------------------------------------------------------ #
    #  DAGs (exists / wait / pause / unpause)                              #
    # ------------------------------------------------------------------ #

    async def get_dag(self, dag_id: str) -> DAGResponse:
        """GET /dags/{dag_id}."""
        resp = await self._api.dags.get(dag_id)
        return _parse(resp, DAGResponse)

    async def list_dags(self, **kwargs: Any) -> List[DAGResponse]:
        """Список DAG-ов (фильтры — tags/paused/only_active/... — пробрасываются)."""
        resp = await self._api.dags.list(**kwargs)
        return _parse(resp, DAGCollectionResponse).dags

    async def dag_exists(self, dag_id: str) -> bool:
        """Проверить, существует ли DAG (удобно в фикстурах и перед триггером).

        Делает GET без валидации статуса/тела: ``200`` → ``True``, ``404`` → ``False``.
        Любой другой статус — это не «нет/есть», а реальная проблема (нет прав,
        5xx и т.п.), поэтому поднимаем :class:`AirflowClientError`.

        Проверяется факт регистрации DAG-а в Airflow: DAG на паузе — существует.
        Обратите внимание, что для DAG-а, чей файл уже удалён из dags-папки,
        Airflow какое-то время продолжает отдавать ``200`` (запись остаётся в БД
        как неактивная/stale), хотя в выдаче ``list_dags`` его уже нет.
        """
        resp = await self._api.dags.get(
            dag_id, validate_status=False, validate_response=False,
        )
        if resp.status_code == HTTPStatus.OK:
            logger.debug("DAG '%s' exists", dag_id)
            return True
        if resp.status_code == HTTPStatus.NOT_FOUND:
            logger.debug("DAG '%s' does not exist", dag_id)
            return False
        raise AirflowClientError(
            f"Unexpected status {resp.status_code} while checking DAG "
            f"'{dag_id}': {resp.text}"
        )

    async def wait_dag(
            self,
            dag_id: str,
            *,
            timeout: float = DEFAULT_WAIT_TIMEOUT,
            poll_interval: float = DEFAULT_POLL_INTERVAL,
            should_exist: bool = True,
    ) -> Optional[DAGResponse]:
        """Дождаться появления DAG-а в Airflow (поллинг :meth:`dag_exists`).

        Нужен, когда DAG выкатывается в dags-папку и в API появляется не сразу —
        только после очередного парсинга планировщиком: до этого ``get_dag`` и
        ``trigger_dag`` отдают 404. При ``should_exist=False`` ждём обратного —
        что DAG пропал (например, после удаления DAG-файла в teardown).

        Возвращает :class:`DAGResponse` дождавшегося DAG-а (при ``should_exist=False``
        — ``None``, возвращать нечего). Бросает :class:`WaitTimeoutError`, если за
        ``timeout`` условие не выполнилось.
        """
        target = "appear" if should_exist else "disappear"

        with allure.step(f"Wait for DAG '{dag_id}' to {target}"):
            # _poll отдаёт None только по таймауту: при should_exist=False
            # успешный результат — это False, поэтому сравниваем с None.
            result = await self._poll(
                lambda: self.dag_exists(dag_id),
                lambda exists: exists is should_exist,
                timeout=timeout,
                poll_interval=poll_interval,
                label=f"DAG '{dag_id}' to {target}",
            )
        if result is None:
            logger.error("DAG '%s' did not %s within %ss", dag_id, target, timeout)
            raise WaitTimeoutError(f"DAG '{dag_id}' did not {target} within {timeout}s")

        logger.info("DAG '%s' %s", dag_id, "appeared" if should_exist else "disappeared")
        return await self.get_dag(dag_id) if should_exist else None

    async def set_dag_paused(self, dag_id: str, is_paused: bool) -> DAGResponse:
        """PATCH /dags/{dag_id} — выставить is_paused."""
        with allure.step(f"{'Pause' if is_paused else 'Unpause'} DAG '{dag_id}'"):
            resp = await self._api.dags.patch(dag_id, DAGPatchBody(is_paused=is_paused))
        logger.info("%s DAG '%s'", "Paused" if is_paused else "Unpaused", dag_id)
        return _parse(resp, DAGResponse)

    async def pause_dag(self, dag_id: str) -> DAGResponse:
        """Поставить DAG на паузу (is_paused=True)."""
        return await self.set_dag_paused(dag_id, True)

    async def unpause_dag(self, dag_id: str) -> DAGResponse:
        """Снять DAG с паузы (is_paused=False)."""
        return await self.set_dag_paused(dag_id, False)

    # ------------------------------------------------------------------ #
    #  Connections                                                         #
    # ------------------------------------------------------------------ #

    async def create_connection(
            self,
            connection_id: str,
            conn_type: str,
            *,
            description: Optional[str] = None,
            host: Optional[str] = None,
            login: Optional[str] = None,
            schema: Optional[str] = None,
            port: Optional[int] = None,
            password: Optional[str] = None,
            extra: Optional[str] = None,
    ) -> ConnectionResponse:
        """POST /connections — создать соединение."""
        body = ConnectionBody(
            connection_id=connection_id,
            conn_type=conn_type,
            description=description,
            host=host,
            login=login,
            schema=schema,
            port=port,
            password=password,
            extra=extra,
        )
        with allure.step(f"Create connection '{connection_id}'"):
            resp = await self._api.connections.create(body)
        logger.info("Created connection '%s' (conn_type=%s)", connection_id, conn_type)
        return _parse(resp, ConnectionResponse)

    async def create_connection_from_dict(self, payload: dict) -> ConnectionResponse:
        """POST /connections — создать соединение из готового JSON (словаря).

        Тело уходит как есть; ключи — как в REST API (``connection_id``,
        ``conn_type``, ``host``, ``login``, ``schema``, ``port``, ``password``,
        ``extra``). Удобно, когда набор параметров уже собран словарём.
        """
        conn_id = payload.get("connection_id")
        with allure.step(f"Create connection '{conn_id}'"):
            resp = await self._api.connections.create(payload)
        logger.info("Created connection '%s' (conn_type=%s)", conn_id, payload.get("conn_type"))
        return _parse(resp, ConnectionResponse)

    async def get_connection(self, connection_id: str) -> ConnectionResponse:
        """GET /connections/{connection_id}."""
        resp = await self._api.connections.get(connection_id)
        return _parse(resp, ConnectionResponse)

    async def connection_exist(self, connection_id: str) -> bool:
        """Проверить, существует ли соединение (удобно в фикстурах set up/tear down).

        Делает GET без валидации статуса/тела: ``200`` → ``True``, ``404`` → ``False``.
        Любой другой статус — это не «нет/есть», а реальная проблема (нет прав,
        5xx и т.п.), поэтому поднимаем :class:`AirflowClientError`.
        """
        resp = await self._api.connections.get(
            connection_id, validate_status=False, validate_response=False,
        )
        if resp.status_code == HTTPStatus.OK:
            logger.debug("Connection '%s' exists", connection_id)
            return True
        if resp.status_code == HTTPStatus.NOT_FOUND:
            logger.debug("Connection '%s' does not exist", connection_id)
            return False
        raise AirflowClientError(
            f"Unexpected status {resp.status_code} while checking connection "
            f"'{connection_id}': {resp.text}"
        )

    async def list_connections(self, **kwargs: Any) -> List[ConnectionCollectionItem]:
        """Список соединений (limit/offset/order_by пробрасываются)."""
        resp = await self._api.connections.list(**kwargs)
        return _parse(resp, ConnectionCollectionResponse).connections

    async def update_connection(
            self,
            connection_id: str,
            body: ConnectionBody,
            *,
            update_mask: Optional[List[str]] = None,
    ) -> ConnectionResponse:
        """PATCH /connections/{connection_id}."""
        resp = await self._api.connections.patch(connection_id, body, update_mask=update_mask)
        logger.info("Updated connection '%s'", connection_id)
        return _parse(resp, ConnectionResponse)

    async def delete_connection(self, connection_id: str) -> None:
        """DELETE /connections/{connection_id}."""
        await self._api.connections.delete(connection_id)
        logger.info("Deleted connection '%s'", connection_id)

    async def test_connection(self, body: ConnectionBody) -> ConnectionTestResponse:
        """POST /connections/test — проверить соединение."""
        resp = await self._api.connections.test(body)
        result = _parse(resp, ConnectionTestResponse)
        logger.info("Tested connection '%s': status=%s", body.connection_id, result.status)
        return result

    # ------------------------------------------------------------------ #
    #  Variables                                                           #
    # ------------------------------------------------------------------ #

    async def set_variable(
            self,
            key: str,
            value: str,
            *,
            description: Optional[str] = None,
    ) -> VariableResponse:
        """POST /variables — создать переменную."""
        body = VariableBody(key=key, value=value, description=description)
        with allure.step(f"Set variable '{key}'"):
            resp = await self._api.variables.create(body)
        logger.info("Set variable '%s'", key)
        return _parse(resp, VariableResponse)

    async def get_variable(self, key: str) -> VariableResponse:
        """GET /variables/{variable_key}."""
        resp = await self._api.variables.get(key)
        return _parse(resp, VariableResponse)

    async def list_variables(self, **kwargs: Any) -> List[VariableCollectionItem]:
        """Список переменных (limit/offset/order_by пробрасываются)."""
        resp = await self._api.variables.list(**kwargs)
        return _parse(resp, VariableCollectionResponse).variables

    async def update_variable(
            self,
            key: str,
            value: str,
            *,
            description: Optional[str] = None,
            update_mask: Optional[List[str]] = None,
    ) -> VariableResponse:
        """PATCH /variables/{variable_key}."""
        body = VariableBody(key=key, value=value, description=description)
        resp = await self._api.variables.patch(key, body, update_mask=update_mask)
        logger.info("Updated variable '%s'", key)
        return _parse(resp, VariableResponse)

    async def delete_variable(self, key: str) -> None:
        """DELETE /variables/{variable_key}."""
        await self._api.variables.delete(key)
        logger.info("Deleted variable '%s'", key)

    # ------------------------------------------------------------------ #
    #  Pools                                                               #
    # ------------------------------------------------------------------ #

    async def create_pool(
            self,
            name: str,
            slots: int,
            *,
            description: Optional[str] = None,
            include_deferred: Optional[bool] = None,
    ) -> PoolResponse:
        """POST /pools — создать пул."""
        body = PoolBody(
            name=name,
            slots=slots,
            description=description,
            include_deferred=include_deferred,
        )
        with allure.step(f"Create pool '{name}'"):
            resp = await self._api.pools.create(body)
        logger.info("Created pool '%s' (slots=%s)", name, slots)
        return _parse(resp, PoolResponse)

    async def get_pool(self, name: str) -> PoolResponse:
        """GET /pools/{pool_name}."""
        resp = await self._api.pools.get(name)
        return _parse(resp, PoolResponse)

    async def list_pools(self, **kwargs: Any) -> List[PoolResponse]:
        """Список пулов (limit/offset/order_by пробрасываются)."""
        resp = await self._api.pools.list(**kwargs)
        return _parse(resp, PoolCollectionResponse).pools

    async def update_pool(
            self,
            name: str,
            *,
            slots: Optional[int] = None,
            description: Optional[str] = None,
            include_deferred: Optional[bool] = None,
            update_mask: Optional[List[str]] = None,
    ) -> PoolResponse:
        """PATCH /pools/{pool_name}."""
        body = PoolBody(
            name=name,
            slots=slots,
            description=description,
            include_deferred=include_deferred,
        )
        resp = await self._api.pools.patch(name, body, update_mask=update_mask)
        logger.info("Updated pool '%s'", name)
        return _parse(resp, PoolResponse)

    async def delete_pool(self, name: str) -> None:
        """DELETE /pools/{pool_name}."""
        await self._api.pools.delete(name)
        logger.info("Deleted pool '%s'", name)

    # ------------------------------------------------------------------ #
    #  Monitoring (health / version)                                       #
    # ------------------------------------------------------------------ #

    async def get_health(self) -> HealthInfoResponse:
        """GET /health — состояние компонентов Airflow (metadatabase/scheduler/...)."""
        resp = await self._api.monitor.health()
        return _parse(resp, HealthInfoResponse)

    async def get_version(self) -> VersionInfo:
        """GET /version — версия Airflow."""
        resp = await self._api.monitor.version()
        return _parse(resp, VersionInfo)

    # ------------------------------------------------------------------ #
    #  Polling primitive                                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    async def _poll(fetch, is_done, *, timeout: float, poll_interval: float, label: str = "operation"):
        """Поллить ``fetch()`` пока ``is_done(result)`` не вернёт True или не выйдет время.

        Возвращает результат при успехе, либо ``None`` если истёк ``timeout``.
        Детали итераций пишутся в DEBUG — на дефолтном INFO они не засоряют вывод тестов.
        """
        deadline = time.monotonic() + timeout
        attempt = 0
        while True:
            attempt += 1
            try:
                result = await fetch()
            except Exception:
                logger.exception("Polling %s failed on attempt %d", label, attempt)
                raise
            if is_done(result):
                logger.debug("Polling %s done on attempt %d", label, attempt)
                return result
            if time.monotonic() >= deadline:
                logger.debug("Polling %s timed out after %d attempt(s)", label, attempt)
                return None
            logger.debug(
                "Polling %s: attempt %d not done, sleeping %.1fs", label, attempt, poll_interval,
            )
            await asyncio.sleep(poll_interval)


def _parse(response, model: Type[M]) -> M:
    """Распарсить тело ``httpx.Response`` в pydantic-модель."""
    return model.model_validate(response.json())
