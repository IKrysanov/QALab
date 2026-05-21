"""Пример использования агрегатора проверок"""

import requests
import allure
from utils.assertions import AssertionAggregator


class TestAggregator:
    URL = "https://jsonplaceholder.typicode.com/posts"

    def test_example_positive(self):
        with allure.step("Request"):
            response = requests.get(self.URL)

            with AssertionAggregator() as aggregator:
                aggregator.assert_equal(response.status_code, 200)
                aggregator.assert_equal(response.json()[0]["userId"], 1)

    def test_example_negative(self):
        with allure.step("Request"):
            response = requests.get(self.URL)

            with AssertionAggregator() as aggregator:
                aggregator.assert_equal(response.status_code, 404)
                aggregator.assert_equal(response.json()[0]["userId"], 2)
