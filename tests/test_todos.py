import allure
import pytest

from src.async_api_client.models.todos import Todo


@allure.epic("JSONPlaceholder")
@allure.feature("Todos")
class TestTodos:

    @allure.title("GET /todos возвращает 200 задач")
    async def test_list_all_todos(self, api_client):
        response = await api_client.todos.list()
        todos = [Todo.model_validate(t) for t in response.json()]
        assert len(todos) == 200

    @allure.title("Фильтр completed=true: все возвращённые задачи завершены")
    async def test_filter_completed_true(self, api_client):
        response = await api_client.todos.list(completed=True)
        todos = [Todo.model_validate(t) for t in response.json()]

        assert len(todos) > 0
        assert all(t.completed is True for t in todos)

    @allure.title("Фильтр completed=false: все возвращённые задачи активны")
    async def test_filter_completed_false(self, api_client):
        response = await api_client.todos.list(completed=False)
        todos = [Todo.model_validate(t) for t in response.json()]

        assert len(todos) > 0
        assert all(t.completed is False for t in todos)

    @allure.title("Суммарное число todo каждого пользователя — 20")
    @pytest.mark.parametrize("user_id", [1, 5, 10])
    async def test_each_user_has_20_todos(self, api_client, user_id):
        response = await api_client.todos.list(user_id=user_id)
        todos = response.json()
        assert len(todos) == 20
        assert all(t["userId"] == user_id for t in todos)