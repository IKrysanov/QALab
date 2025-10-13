import time
from typing import Optional, Dict, Any, List
from pathlib import Path
import allure
import logging
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, Response
import subprocess
import os

from src.web_ui.exceptions.web_exceptions import WebClientException


class WebClientSE:
    """
    Web UI клиент для автоматизации тестирования на основе Playwright.

    Основные возможности:
    - Управление браузером Browser (подключение/отключение)
    - Навигация по страницам (переходы, обновление, история)
    - Управление вкладками/страницами
    - Создание скриншотов с автоматическим прикреплением к Allure отчетам
    - Очистка кеша, cookies и локального хранилища
    - Получение информации о странице (URL, заголовок)
    - Ожидание состояний загрузки

    Особенности:
    - Работает с Browser через системный путь
    - Автоматически скрывает признаки автоматизации
    - Поддерживает контекстный менеджер для безопасного управления ресурсами
    - Интегрирован с Allure для отчетности

    Пример использования:
    ```python
    with WebClient("example.com") as client:
        client.navigate("/login")
        client.take_screenshot("login_page")
        print(f"Title: {client.get_page_title()}")
    ```

    Attributes:
        base_url (str): Базовый URL для навигации
        headless (bool): Режим без графического интерфейса
        slow_mo (int): Задержка между действиями в миллисекундах
    """

    def __init__(
            self,
            base_url: str,
            browser_type: str = "chromium",
            schema_http: str = "https",
            headless: bool = True,
            slow_mo: int = 0,
            timeout: int = 30000,
    ):
        self.base_url = f"{schema_http}://{base_url}" if not base_url.startswith(('http://', 'https://')) else base_url
        self.base_url = self.base_url.rstrip('/')
        self.headless = headless
        self.slow_mo = slow_mo
        self.browser_type = browser_type
        self.default_timeout = timeout
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._is_connected = False
        self._screenshot_counter = 0
        self.logger = logging.getLogger(__name__)

    @allure.step("[Browser]Подключение и инициализация")
    def connect(self) -> bool:
        """
       Подключение к Browser и инициализация контекста.

       Returns:
           bool: True если подключение успешно, False в случае ошибки

       Raises:
           WebClientException: При критических ошибках инициализации
       """

        try:
            self.playwright = sync_playwright().start()

            self.browser = getattr(self.playwright, self.browser_type).launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                    "--disable-blink-features=AutomationControlled",
                    "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
                ],
                slow_mo=self.slow_mo
            )

            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                ignore_https_errors=True,
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                           ' AppleWebKit/537.36 (KHTML, like Gecko)'
                           ' Chrome/120.0.0.0 Safari/537.36',
                bypass_csp=True
            )

            self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
            """)

            self.page = self.context.new_page()
            self._is_connected = True

            self.logger.info("Web client connected to Browser successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to connect to Browser: {e}")
            if self.playwright:
                self.playwright.stop()
            return False

    def get_page_info(self) -> Dict[str, Any]:
        """Получение информации о текущей странице"""

        if not self.is_connected():
            return {}

        return {
            "url": self.page.url,
            "title": self.page.title(),
            "pages_count": len(self.context.pages),
            "viewport_size": self.page.viewport_size
        }

    def close_all_pages_except_current(self) -> None:
        """Закрытие всех страниц кроме текущей"""

        if not self.is_connected():
            return

        pages = self.context.pages
        for page in pages:
            if page != self.page and not page.is_closed():
                page.close()

        self.logger.info(f"Closed {len(pages) - 1} pages, kept current page")

    @allure.step("Переход по URL: {url}")
    def navigate(
            self, url: str = "", timeout: int = 30000, take_screenshot: bool = True, screenshot_name: str = None
    ) -> Optional[Response]:
        """
        Переход по URL с опциональным созданием скриншота.

        Args:
            url: Относительный или абсолютный URL для перехода
            timeout: Таймаут навигации в миллисекундах
            take_screenshot: Создавать ли скриншот для Allure
            screenshot_name: Кастомное имя для скриншота

        Returns:
            Optional[Response]: Объект ответа сервера или None
        """

        if not self.is_connected():
            raise WebClientException("Web client is not connected")

        full_url = f"{self.base_url}/{url.lstrip('/')}" if url else self.base_url
        self.logger.info(f"Navigating to: {full_url}")

        try:
            response = self.page.goto(full_url, timeout=timeout, wait_until="networkidle")
            self.page.wait_for_load_state("networkidle")

            if take_screenshot:
                name = screenshot_name or f"navigate_success_{url.replace('/', '_') if url else 'home'}"
                self._take_screenshot_to_allure_only(name)

            return response

        except Exception as e:
            self.logger.error(f"Navigation failed: {e}")

            if take_screenshot:
                name = screenshot_name or f"navigation_error_{url.replace('/', '_') if url else 'home'}"
                self._take_screenshot_to_allure_only(name)

            raise WebClientException(f"Navigation failed: {e}")

    def go_back(self, timeout: int = 30000) -> None:
        """Возврат на предыдущую страницу"""

        if not self.is_connected():
            raise WebClientException("Web client is not connected")

        self.logger.info("Going back to previous page")
        self.page.go_back(timeout=timeout, wait_until="networkidle")

    def go_forward(self, timeout: int = 30000) -> None:
        """Переход вперед по истории"""

        if not self.is_connected():
            raise WebClientException("Web client is not connected")

        self.logger.info("Going forward to next page")
        self.page.go_forward(timeout=timeout, wait_until="networkidle")

    def create_new_page(self) -> Page:
        """Создание новой страницы в текущем контексте"""

        if not self.is_connected():
            raise WebClientException("Web client is not connected")

        new_page = self.context.new_page()
        self.logger.info("New page created")
        return new_page

    def switch_to_page(self, page_index: int = 0) -> Optional[Page]:
        """Переключение на другую страницу по индексу"""

        if not self.is_connected() or not self.context:
            return None

        pages = self.context.pages
        if 0 <= page_index < len(pages):
            self.page = pages[page_index]
            self.logger.info(f"Switched to page {page_index}")
            return self.page

        self.logger.warning(f"Page index {page_index} out of range")
        return None

    def close_current_page(self) -> None:
        """Закрытие текущей страницы"""

        if not self.is_connected():
            return

        if len(self.context.pages) > 1:
            self.page.close()

            self.page = self.context.pages[0]
            self.logger.info("Current page closed")
        else:
            self.logger.warning("Cannot close the only page")

    def clear_cache(self) -> None:
        """
        Очистка кеша браузера (cache storage).

        Удаляет закешированные ресурсы, но сохраняет cookies и localStorage.
        """

        if not self.is_connected():
            return

        try:
            self.context.clear_cache()
            self.logger.info("Browser cache cleared successfully")
        except Exception as e:
            self.logger.error(f"Failed to clear cache: {e}")

    def clear_cookies(self) -> None:
        """
        Очистка всех cookies для текущего контекста.

        Удаляет все cookies для текущего домена и поддоменов.
        """

        if not self.is_connected():
            return

        try:
            self.context.clear_cookies()
            self.logger.info("Cookies cleared successfully")
        except Exception as e:
            self.logger.error(f"Failed to clear cookies: {e}")

    def clear_local_storage(self) -> None:
        """
        Очистка localStorage и sessionStorage текущей страницы.
        """

        if not self.is_connected():
            return

        try:
            self.page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
            self.logger.info("Local storage and session storage cleared")
        except Exception as e:
            self.logger.error(f"Failed to clear local storage: {e}")

    def clear_all_data(self) -> None:
        """
        Комплексная очистка всех данных браузера.

        Выполняет очистку:
        - Кеша браузера
        - Cookies
        - localStorage и sessionStorage
        """

        self.logger.info("Clearing all browser data")
        self.clear_cache()
        self.clear_cookies()
        self.clear_local_storage()
        self.logger.info("All browser data cleared")

    def get_cookies(self) -> List[Dict[str, Any]]:
        """
        Получение всех cookies текущего контекста.

        Returns:
            List[Dict]: Список cookies с их атрибутами
        """

        if not self.is_connected():
            return []

        try:
            cookies = self.context.cookies()
            self.logger.info(f"Retrieved {len(cookies)} cookies")
            if cookies:
                return cookies
            else:
                return []

        except Exception as e:
            self.logger.error(f"Failed to get cookies: {e}")
            return []

    @allure.step("Создание скриншота текущей страницы")
    def take_screenshot(self, name: str, path: str = "screenshots") -> Optional[Path]:
        """Создание скриншота текущей страницы"""

        if not self.is_connected():
            return None

        try:
            screenshot_path = Path(path) / f"{name}.png"
            screenshot_path.parent.mkdir(exist_ok=True, parents=True)

            screenshot_bytes = self.page.screenshot(full_page=True, type="png")

            with open(screenshot_path, 'wb') as f:
                f.write(screenshot_bytes)

            allure.attach(
                screenshot_bytes,
                name=name,
                attachment_type=allure.attachment_type.PNG
            )

            self.logger.info(f"Screenshot saved and attached to Allure: {screenshot_path}")
            return screenshot_path

        except Exception as e:
            self.logger.error(f"Screenshot failed: {e}")
            return None

    @allure.step("Ожидание определенного состояния загрузки")
    def wait_for_load_state(self, state: str = "networkidle", timeout: int = 30000) -> None:
        """Ожидание определенного состояния загрузки"""

        if self.is_connected():
            self.page.wait_for_load_state(state, timeout=timeout)

    def is_connected(self) -> bool:
        """
        Проверка активности подключения к браузеру.

        Returns:
            bool: True если браузер подключен и страница активна
        """

        return self._is_connected and self.page is not None and not self.page.is_closed()

    def _check_browser_version(self, _path: str):
        """Проверка версии Browser"""

        try:
            result = subprocess.run(
                [_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                self.logger.info(f"Browser version: {result.stdout.strip()}")
            else:
                self.logger.warning("Could not determine Browser version")
        except Exception as e:
            self.logger.warning(f"Failed to check Browser version: {e}")

    def _take_screenshot_to_allure_only(self, name: str) -> None:
        """
        Создание скриншота только для Allure без сохранения на диск.

        Args:
            name: Имя скриншота в Allure
        """

        if not self.is_connected():
            return

        try:
            screenshot_bytes = self.page.screenshot(full_page=True, type="png")
            allure.attach(
                screenshot_bytes,
                name=name,
                attachment_type=allure.attachment_type.PNG
            )
            self.logger.info(f"Screenshot attached to Allure (memory only): {name}")

        except Exception as e:
            self.logger.error(f"Memory screenshot failed: {e}")

    @classmethod
    @allure.step("Клиент спит {sec} секунд")
    def sleep(cls, sec: int | float) -> None:
        """Sleep"""

        time.sleep(sec)

    @allure.step("Отключение от браузера")
    def disconnect(self) -> bool:
        """Отключение от браузера"""

        try:
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()

            self._is_connected = False
            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None
            self.clear_all_data()

            self.logger.info("Web client disconnected")
            return True

        except Exception as e:
            self.logger.error(f"Error disconnecting web client: {e}")
            return False

    def __enter__(self):
        """Поддержка контекстного менеджера"""

        try:
            if not self.connect():
                raise WebClientException("Failed to connect to browser")
            return self
        except Exception as e:
            self.logger.error(f"Error in context manager: {e}")
            self.disconnect()
            raise

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Выход из контекстного менеджера"""

        if exc_type:
            self.logger.error(f"Exception in context: {exc_type.__name__}: {exc_val}")
            if self.is_connected():
                self._take_screenshot_to_allure_only("context_exit_error")

        self.disconnect()
