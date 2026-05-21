"""
Архитектура:
- Каждая проверка — отдельный класс (Check), реализующий протокол AssertionCheck.
  Новую проверку можно добавить, не трогая агрегатор (OCP).
- AssertionAggregator не знает про конкретные проверки и про Allure —
  он работает с абстракциями ErrorCollector и ErrorReporter (DIP).
- Интерфейсы узкие: коллектор только собирает, репортер только публикует (ISP).
- Публичный API (контекстный менеджер + методы assert_*) сохранён.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Iterable, List, Optional, Protocol, Type

import allure

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Абстракции (DIP, ISP)
# ---------------------------------------------------------------------------


class AssertionCheck(Protocol):
    """Протокол одной проверки.

    Каждая конкретная проверка должна уметь выполнить себя и вернуть
    текст ошибки, либо None, если проверка прошла. No side-effects.
    """

    def check(self) -> Optional[str]: ...


class ErrorCollector(Protocol):
    """Собирает сообщения об ошибках."""

    def add(self, message: str) -> None: ...

    @property
    def errors(self) -> List[str]: ...

    def clear(self) -> None: ...


class ErrorReporter(Protocol):
    """Публикует агрегированный отчёт об ошибках."""

    def report(self, errors: List[str]) -> None: ...


# ---------------------------------------------------------------------------
# Реализации коллектора и репортера
# ---------------------------------------------------------------------------


class InMemoryErrorCollector:
    """Хранит ошибки в списке в памяти."""

    def __init__(self) -> None:
        self._errors: List[str] = []

    def add(self, message: str) -> None:
        self._errors.append(message)

    @property
    def errors(self) -> List[str]:
        return list(self._errors)

    def clear(self) -> None:
        self._errors.clear()


class AllureErrorReporter:
    def report(self, errors: List[str]) -> None:
        with allure.step(f"Отчёт об ошибках: {len(errors)}"):
            if not errors:
                return

            aggregated = "\n".join(errors)
            final_message = f"Найдены ошибки!\n{aggregated}\n"

            logger.error(final_message)
            raise AssertionError(final_message)


# ---------------------------------------------------------------------------
# Конкретные проверки (SRP, OCP)
# ---------------------------------------------------------------------------


class _BaseCheck(ABC):
    """Базовый класс — хранит сообщение пользователя и формирует префикс."""

    def __init__(self, message: str = "") -> None:
        self._message = message

    @abstractmethod
    def check(self) -> Optional[str]:
        ...

    def _format(self, detail: str) -> str:
        prefix = f"Ошибка: {self._message}. " if self._message else "Ошибка: "
        return f"{prefix}{detail}"


class EqualCheck(_BaseCheck):
    """Проверка на равенство двух значений.

    Проверяет, что фактическое значение равно ожидаемому.

    Args:
        actual: Фактическое значение для проверки.
        expected: Ожидаемое значение.
        message: Дополнительное сообщение об ошибке.

    Returns:
        None если значения равны, иначе сообщение об ошибке.
    """

    def __init__(self, actual: Any, expected: Any, message: str = "") -> None:
        super().__init__(message)
        self._actual = actual
        self._expected = expected

    def check(self) -> Optional[str]:
        if self._actual == self._expected:
            return None
        return self._format(
            f"Ожидалось: {self._expected!r}, но получено: {self._actual!r}"
        )


class NotEqualCheck(_BaseCheck):
    """Проверка на неравенство двух значений.

    Проверяет, что фактическое значение не равно неожиданному.

    Args:
        actual: Фактическое значение для проверки.
        unexpected: Неожиданное значение.
        message: Дополнительное сообщение об ошибке.

    Returns:
        None если значения не равны, иначе сообщение об ошибке.
    """

    def __init__(self, actual: Any, unexpected: Any, message: str = "") -> None:
        super().__init__(message)
        self._actual = actual
        self._unexpected = unexpected

    def check(self) -> Optional[str]:
        if self._actual != self._unexpected:
            return None
        return self._format(
            f"Неожиданно, что {self._actual!r} == {self._unexpected!r}"
        )


class TrueCheck(_BaseCheck):
    """Проверка, что условие истинно.

    Проверяет, что переданное условие имеет истинное значение.

    Args:
        condition: Условие для проверки.
        message: Дополнительное сообщение об ошибке.

    Returns:
        None если условие истинно, иначе сообщение об ошибке.
    """

    def __init__(self, condition: Any, message: str = "") -> None:
        super().__init__(message)
        self._condition = condition

    def check(self) -> Optional[str]:
        if self._condition:
            return None
        return self._format(f"Условие не выполнено: {self._condition!r}")


class FalseCheck(_BaseCheck):
    """Проверка, что условие ложно.

    Проверяет, что переданное условие имеет ложное значение.

    Args:
        condition: Условие для проверки.
        message: Дополнительное сообщение об ошибке.

    Returns:
        None если условие ложно, иначе сообщение об ошибке.
    """

    def __init__(self, condition: Any, message: str = "") -> None:
        super().__init__(message)
        self._condition = condition

    def check(self) -> Optional[str]:
        if not self._condition:
            return None
        return self._format(f"Условие должно быть ложным: {self._condition!r}")


class IsInstanceCheck(_BaseCheck):
    """Проверка типа объекта.

    Проверяет, что объект является экземпляром указанного класса или одного из классов.

    Args:
        obj: Объект для проверки.
        classinfo: Класс или кортеж классов для проверки типа.
        message: Дополнительное сообщение об ошибке.

    Returns:
        None если объект является экземпляром указанного класса, иначе сообщение об ошибке.
    """

    def __init__(
            self,
            obj: Any,
            classinfo: Type[Any] | tuple,
            message: str = "",
    ) -> None:
        super().__init__(message)
        self._obj = obj
        self._classinfo = classinfo

    def check(self) -> Optional[str]:
        if isinstance(self._obj, self._classinfo):
            return None
        return self._format(
            f"{self._obj!r} не является экземпляром {self._classinfo}"
        )


class InCheck(_BaseCheck):
    """Проверка, что элемент находится в контейнере.

    Проверяет, что элемент присутствует в указанном контейнере.

    Args:
        item: Элемент для поиска.
        container: Контейнер, в котором выполняется поиск.
        message: Дополнительное сообщение об ошибке.

    Returns:
        None если элемент найден, иначе сообщение об ошибке.
    """

    def __init__(self, item: Any, container: Any, message: str = "") -> None:
        super().__init__(message)
        self._item = item
        self._container = container

    def check(self) -> Optional[str]:
        if self._item in self._container:
            return None
        return self._format(f"{self._item!r} не найдено в {self._container!r}")


class NotInCheck(_BaseCheck):
    """Проверка, что элемент не находится в контейнере.

    Проверяет, что элемент отсутствует в указанном контейнере.

    Args:
        item: Элемент для поиска.
        container: Контейнер, в котором выполняется поиск.
        message: Дополнительное сообщение об ошибке.

    Returns:
        None если элемент не найден, иначе сообщение об ошибке.
    """

    def __init__(self, item: Any, container: Any, message: str = "") -> None:
        super().__init__(message)
        self._item = item
        self._container = container

    def check(self) -> Optional[str]:
        if self._item not in self._container:
            return None
        return self._format(
            f"{self._item!r} не должен присутствовать в {self._container!r}"
        )


class GreaterCheck(_BaseCheck):
    """Проверка, что значение больше ожидаемого.

    Проверяет, что фактическое значение больше ожидаемого.

    Args:
        actual: Фактическое значение для проверки.
        expected: Ожидаемое значение для сравнения.
        message: Дополнительное сообщение об ошибке.

    Returns:
        None если actual > expected, иначе сообщение об ошибке.
    """

    def __init__(self, actual: Any, expected: Any, message: str = "") -> None:
        super().__init__(message)
        self._actual = actual
        self._expected = expected

    def check(self) -> Optional[str]:
        if self._actual > self._expected:
            return None
        return self._format(f"{self._actual!r} не больше, чем {self._expected!r}")


class LessCheck(_BaseCheck):
    """Проверка, что значение меньше ожидаемого.

    Проверяет, что фактическое значение меньше ожидаемого.

    Args:
        actual: Фактическое значение для проверки.
        expected: Ожидаемое значение для сравнения.
        message: Дополнительное сообщение об ошибке.

    Returns:
        None если actual < expected, иначе сообщение об ошибке.
    """

    def __init__(self, actual: Any, expected: Any, message: str = "") -> None:
        super().__init__(message)
        self._actual = actual
        self._expected = expected

    def check(self) -> Optional[str]:
        if self._actual < self._expected:
            return None
        return self._format(f"{self._actual!r} не меньше, чем {self._expected!r}")


class InRangeCheck(_BaseCheck):
    """Проверка, что значение находится в указанном диапазоне.

    Проверяет, что значение находится в пределах от минимума до максимума (включительно).

    Args:
        value: Значение для проверки.
        min_value: Минимальное значение диапазона (включительно).
        max_value: Максимальное значение диапазона (включительно).
        message: Дополнительное сообщение об ошибке.

    Returns:
        None если min_value <= value <= max_value, иначе сообщение об ошибке.
    """

    def __init__(
            self,
            value: Any,
            min_value: Any,
            max_value: Any,
            message: str = "",
    ) -> None:
        super().__init__(message)
        self._value = value
        self._min = min_value
        self._max = max_value

    def check(self) -> Optional[str]:
        if self._min <= self._value <= self._max:
            return None
        return self._format(
            f"{self._value!r} не в пределах диапазона {self._min!r}-{self._max!r}"
        )


class SubsetCheck(_BaseCheck):
    """Проверка, что множество является подмножеством другого.

    Проверяет, что все элементы из subset присутствуют в superset.

    Args:
        subset: Итерируемый объект, который должен быть подмножеством.
        superset: Итерируемый объект, который должен содержать все элементы.
        message: Дополнительное сообщение об ошибке.

    Returns:
        None если subset является подмножеством superset, иначе сообщение об ошибке
        с указанием отсутствующих элементов.
    """

    def __init__(
            self,
            subset: Iterable,
            superset: Iterable,
            message: str = "",
    ) -> None:
        super().__init__(message)
        self._subset = set(subset)
        self._superset = set(superset)

    def check(self) -> Optional[str]:
        if self._subset.issubset(self._superset):
            return None
        missing = self._subset - self._superset
        return self._format(
            f"Набор {self._subset} не является подмножеством {self._superset}. "
            f"Отсутствующие элементы: {missing}"
        )


class SupersetCheck(_BaseCheck):
    """Проверка, что множество является надмножеством другого.

    Проверяет, что superset содержит все элементы из subset.

    Args:
        superset: Итерируемый объект, который должен быть надмножеством.
        subset: Итерируемый объект, элементы которого должны содержаться.
        message: Дополнительное сообщение об ошибке.

    Returns:
        None если superset является надмножеством subset, иначе сообщение об ошибке
        с указанием отсутствующих элементов.
    """

    def __init__(
            self,
            superset: Iterable,
            subset: Iterable,
            message: str = "",
    ) -> None:
        super().__init__(message)
        self._superset = set(superset)
        self._subset = set(subset)

    def check(self) -> Optional[str]:
        if self._superset.issuperset(self._subset):
            return None
        missing = self._subset - self._superset
        return self._format(
            f"Набор {self._superset} не является надмножеством {self._subset}. "
            f"Отсутствующие элементы: {missing}"
        )


# ---------------------------------------------------------------------------
# Агрегатор (фасад для пользователя)
# ---------------------------------------------------------------------------


class AssertionAggregator:
    """Контекстный менеджер для soft-assertions.

    Принцип работы: каждый assert_* строит объект-проверку (Check),
    выполняет его и складывает ошибку в коллектор. На выходе из `with`
    репортер публикует агрегированный отчёт.

    Зависимости (коллектор и репортер) внедряются через конструктор —
    их можно подменить в тестах или для другой системы отчётности.
    """

    def __init__(
            self,
            collector: Optional[ErrorCollector] = None,
            reporter: Optional[ErrorReporter] = None,
    ) -> None:
        self._collector: ErrorCollector = collector or InMemoryErrorCollector()
        self._reporter: ErrorReporter = reporter or AllureErrorReporter()

    def __enter__(self) -> "AssertionAggregator":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is not None:
            return False
        self.finalize()
        return False

    def assert_equal(self, actual: Any, expected: Any, message: str = "") -> None:
        """Проверяет, что два значения равны.

        Args:
            actual: Фактическое значение.
            expected: Ожидаемое значение.
            message: Дополнительное сообщение об ошибке.
        """

        self._run(EqualCheck(actual, expected, message))

    def assert_not_equal(self, actual: Any, expected: Any, message: str = "") -> None:
        """Проверяет, что два значения не равны.

        Args:
            actual: Фактическое значение.
            expected: Значение, которое не должно быть равно actual.
            message: Дополнительное сообщение об ошибке.
        """

        self._run(NotEqualCheck(actual, expected, message))

    def assert_true(self, condition: Any, message: str = "") -> None:
        """Проверяет, что условие истинно.

        Args:
            condition: Условие для проверки.
            message: Дополнительное сообщение об ошибке.
        """

        self._run(TrueCheck(condition, message))

    def assert_false(self, condition: Any, message: str = "") -> None:
        """Проверяет, что условие ложно.

        Args:
            condition: Условие для проверки.
            message: Дополнительное сообщение об ошибке.
        """

        self._run(FalseCheck(condition, message))

    def assert_is_instance(
            self, obj: Any, classinfo: Type[Any] | tuple, message: str = ""
    ) -> None:
        """Проверяет, что объект является экземпляром указанного класса.

        Args:
            obj: Объект для проверки.
            classinfo: Класс или кортеж классов для проверки типа.
            message: Дополнительное сообщение об ошибке.
        """

        self._run(IsInstanceCheck(obj, classinfo, message))

    def assert_in(self, item: Any, container: Any, message: str = "") -> None:
        """Проверяет, что элемент находится в контейнере.

        Args:
            item: Элемент для поиска.
            container: Контейнер, в котором выполняется поиск.
            message: Дополнительное сообщение об ошибке.
        """

        self._run(InCheck(item, container, message))

    def assert_not_in(self, item: Any, container: Any, message: str = "") -> None:
        """Проверяет, что элемент не находится в контейнере.

        Args:
            item: Элемент для поиска.
            container: Контейнер, в котором выполняется поиск.
            message: Дополнительное сообщение об ошибке.
        """

        self._run(NotInCheck(item, container, message))

    def assert_greater(self, actual: Any, expected: Any, message: str = "") -> None:
        """Проверяет, что значение больше ожидаемого.

        Args:
            actual: Фактическое значение.
            expected: Значение для сравнения.
            message: Дополнительное сообщение об ошибке.
        """

        self._run(GreaterCheck(actual, expected, message))

    def assert_less(self, actual: Any, expected: Any, message: str = "") -> None:
        """Проверяет, что значение меньше ожидаемого.

        Args:
            actual: Фактическое значение.
            expected: Значение для сравнения.
            message: Дополнительное сообщение об ошибке.
        """

        self._run(LessCheck(actual, expected, message))

    def assert_in_range(
            self, value: Any, min_value: Any, max_value: Any, message: str = ""
    ) -> None:
        """Проверяет, что значение находится в указанном диапазоне.

        Args:
            value: Значение для проверки.
            min_value: Минимальное значение диапазона (включительно).
            max_value: Максимальное значение диапазона (включительно).
            message: Дополнительное сообщение об ошибке.
        """

        self._run(InRangeCheck(value, min_value, max_value, message))

    def assert_subset(
            self, subset: Iterable, superset: Iterable, message: str = ""
    ) -> None:
        """Проверяет, что множество является подмножеством другого.

        Args:
            subset: Итерируемый объект, который должен быть подмножеством.
            superset: Итерируемый объект, который должен содержать все элементы.
            message: Дополнительное сообщение об ошибке.
        """

        self._run(SubsetCheck(subset, superset, message))

    def assert_superset(
            self, superset: Iterable, subset: Iterable, message: str = ""
    ) -> None:
        """Проверяет, что множество является надмножеством другого.

        Args:
            superset: Итерируемый объект, который должен быть надмножеством.
            subset: Итерируемый объект, элементы которого должны содержаться.
            message: Дополнительное сообщение об ошибке.
        """

        self._run(SupersetCheck(superset, subset, message))

    def run_check(self, check: AssertionCheck) -> None:
        """Запустить произвольную пользовательскую проверку (OCP).

        Позволяет добавить новый тип проверки, не меняя класс агрегатора —
        достаточно реализовать протокол AssertionCheck.
        """

        self._run(check)

    def finalize(self) -> None:
        errors = self._collector.errors
        self._collector.clear()
        self._reporter.report(errors)

    def _run(self, check: AssertionCheck) -> None:
        error = check.check()
        if error is not None:
            self._collector.add(error)
