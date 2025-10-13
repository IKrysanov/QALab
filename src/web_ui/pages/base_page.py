from typing import Optional, List
import logging
from playwright.sync_api import Page, Locator
from src.web_ui.client.web_client import WebClientSE

from src.web_ui.exceptions.web_exceptions import WebClientException


class BasePage:
    """
    Базовый класс для всех Page Objects.

    Содержит общие методы для работы с элементами страницы.
    """

    def __init__(self, page: Page, web_client: WebClientSE = None):
        """
        Инициализация Page Object.

        Args:
            page: Объект страницы Playwright
            web_client: Опционально - ссылка на WebClient для скриншотов
        """
        self.page = page
        self.web_client = web_client
        self.base_url = self.web_client.base_url
        self.logger = logging.getLogger(self.__class__.__name__)

    def navigate(self, path: str = "") -> None:
        """
        Навигация на страницу относительно base_url.

        Args:
            path: Относительный путь (например: "login", "dashboard")
        """

        self._validate_connection()

        url = f"{self.base_url}/{path.lstrip('/')}" if path else self.base_url
        self.logger.info(f"Navigating to: {url}")
        self.page.goto(url)
        self.page.wait_for_load_state("networkidle")

    def get_element(self, selector: str) -> Locator:
        """Получение локатора элемента"""

        return self.page.locator(selector)

    def click(self, selector: str, timeout: int = 30000) -> None:
        """Клик по элементу"""

        self.logger.info(f"Clicking element: {selector}")
        self.page.click(selector, timeout=timeout)

    def fill(self, selector: str, value: str) -> None:
        """Заполнение поля ввода"""

        self.logger.info(f"Filling {selector} with: {value}")
        self.page.fill(selector, value)

    def type_text(self, selector: str, text: str, delay: int = 0) -> None:
        """Ввод текста с имитацией пользовательского ввода"""

        self.logger.info(f"Typing text in {selector}: {text}")
        self.page.type(selector, text, delay=delay)

    def clear_field(self, selector: str) -> None:
        """Очистка поля ввода"""

        self.logger.info(f"Clearing field: {selector}")
        self.page.fill(selector, "")

    def get_text(self, selector: str, timeout: int = 5000) -> Optional[str]:
        """Получение текста элемента"""

        try:
            self.wait_for_element(selector, timeout)
            text = self.page.text_content(selector)
            self.logger.info(f"Text from {selector}: {text}")
            return text

        except Exception as e:
            self.logger.warning(f"Failed to get text from {selector}: {e}")
            return None

    def get_attribute(self, selector: str, attribute: str, timeout: int = 5000) -> Optional[str]:
        """Получение атрибута элемента"""

        try:
            self.wait_for_element(selector, timeout)
            return self.page.get_attribute(selector, attribute)

        except Exception as e:
            self.logger.warning(f"Failed to get attribute {attribute} from {selector}: {e}")
            return None

    def is_visible(self, selector: str, timeout: int = 5000) -> bool:
        """Проверка видимости элемента"""
        try:
            self.page.wait_for_selector(selector, timeout=timeout)
            return self.page.is_visible(selector)

        except Exception:
            return False

    def is_enabled(self, selector: str, timeout: int = 5000) -> bool:
        """Проверка активности элемента"""
        try:
            self.page.wait_for_selector(selector, timeout=timeout)
            return self.page.is_enabled(selector)

        except Exception:
            return False

    def wait_for_element(self, selector: str, timeout: int = 10000) -> None:
        """Ожидание появления элемента"""

        self._validate_connection()
        self.page.wait_for_selector(selector, timeout=timeout)

    def wait_for_element_hidden(self, selector: str, timeout: int = 10000) -> None:
        """Ожидание скрытия элемента"""

        self._validate_connection()
        self.page.wait_for_selector(selector, state="hidden", timeout=timeout)

    def wait_for_url_contains(self, text: str, timeout: int = 10000) -> None:
        """Ожидание URL содержащего текст"""

        self._validate_connection()
        self.page.wait_for_url(lambda url: text in url, timeout=timeout)

    def select_option(self, selector: str, value: str) -> None:
        """Выбор опции в выпадающем списке"""

        self._validate_connection()
        self.logger.info(f"Selecting option {value} in {selector}")
        self.page.select_option(selector, value)

    def check_checkbox(self, selector: str) -> None:
        """Установка чекбокса"""

        if not self.is_checked(selector):
            self.click(selector)

    def uncheck_checkbox(self, selector: str) -> None:
        """Снятие чекбокса"""

        if self.is_checked(selector):
            self.click(selector)

    def is_checked(self, selector: str) -> bool:
        """Проверка установлен ли чекбокс"""

        self._validate_connection()
        return self.page.is_checked(selector)

    def get_current_url(self) -> str:
        """Получение текущего URL"""

        self._validate_connection()
        url = self.page.url
        self.logger.info(f"Текущий URL: {url}")
        return url

    def get_page_title(self) -> str:
        """Получение заголовка текущей страницы"""

        self._validate_connection()
        title = self.page.title()
        self.logger.info(f"Page title: {title}")
        return title

    def refresh_page(self, timeout: int = 30000) -> None:
        """Обновление текущей страницы"""

        self._validate_connection()
        self.logger.info("Refreshing page")
        self.page.reload(timeout=timeout, wait_until="networkidle")

    def _validate_connection(self):
        if self.page.is_closed():
            raise WebClientException("Page is closed")
        if self.web_client and not self.web_client.is_connected():
            raise WebClientException("Web client is not connected")
