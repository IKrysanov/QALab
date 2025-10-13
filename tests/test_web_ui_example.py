from src.web_ui.client.web_client import WebClientSE
from src.web_ui.pages.base_page import BasePage
import pytest

@pytest.fixture(scope="module")
def web_client_fixture():
    """Fixture to create a web client session."""

    with WebClientSE(base_url="google.com",headless=False) as web_client:
        yield web_client

def test_web_ui_example(web_client_fixture):
    """
    Example test function to demonstrate the use of the web_client_fixture.
    """

    accept_selectors = [
        'button:has-text("Принять все")',
        'button:has-text("Accept all")',
        'button:has-text("Я согласен")',
        'button:has-text("I agree")',
        '[id*="accept"] button',
        'form[action*="consent"] button'
    ]

    web_client_fixture.navigate(screenshot_name="test_web_ui_example")
    web_client_fixture.wait_for_load_state()
    web_client_fixture.get_page_info()

    page = web_client_fixture.page
    base_page = BasePage(page=page, web_client=web_client_fixture)

    for selector in accept_selectors:
        if base_page.is_visible(selector):
            base_page.click(selector)
            print("Приняли условия cookies")
            break

    assert "Google" in base_page.get_page_title()
    base_page.fill('textarea[name="q"]', 'Как тестируют в Google?')
    base_page.web_client.page.keyboard.press("Enter")
    web_client_fixture.wait_for_load_state()
    web_client_fixture.create_new_page()
    web_client_fixture.take_screenshot(name="test_web_ui_example")
    web_client_fixture.sleep(10)