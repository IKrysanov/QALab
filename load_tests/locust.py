from locust import HttpUser, TaskSet, SequentialTaskSet, LoadTestShape, task, between, events
import threading

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

auth_token = None
auth_lock = threading.Lock()


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    global auth_token
    auth_token = None
    logger.info("Тест остановлен, токен очищен")


class ImagesTest(TaskSet):
    @task(3)
    def image_png(self):
        response = self.client.get("/image/png")
        logger.info(
            f"Response status {response.status_code} is valid."
            f"Response body length {len(response.content)}"
        )
        self.interrupt()

    @task(1)
    def image_jpeg(self):
        response = self.client.get("/image/jpeg")
        logger.info(
            f"Response status {response.status_code} is valid."
            f"Response body length {len(response.content)}"
        )
        self.interrupt(reschedule=False)


class MethodsTest(SequentialTaskSet):
    @task
    def post(self):
        response = self.client.post("/post")
        logger.info(
            f"Response status {response.status_code} is valid."
            f"Response body {response.text}"
        )

    @task
    def delete(self):
        response = self.client.delete("/delete")
        logger.info(
            f"Response status {response.status_code} is valid."
            f"Response body {response.text}"
        )

    @task
    def get(self):
        response = self.client.get("/get")
        logger.info(
            f"Response status {response.status_code} is valid."
            f"Response body {response.text}"
        )

    @task
    def finish(self):
        logger.info("Transaction 'MethodsTest' finished.")
        self.interrupt()


class LoadTestUser(HttpUser):
    wait_time = between(1, 3)
    host = "https://httpbin.org"
    tasks = {MethodsTest: 3, ImagesTest: 3}
    verify = False

    def on_start(self):
        global auth_token
        with auth_lock:
            if not auth_token:
                self.client.get("/bearer")
                auth_token = "131"

        self.client.headers = {"Authorization": f"Bearer {auth_token}"}

    def on_stop(self):
        logger.info(f"[User {self.id}] Завершил работу")


class StepLoadShape(LoadTestShape):
    stages = [
        {"duration": 10, "users": 1, "spawn_rate": 1},
        {"duration": 360, "users": 2, "spawn_rate": 1}
    ]

    def tick(self):
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                tick_data = (stage["users"], stage["spawn_rate"])
                return tick_data

        return None
