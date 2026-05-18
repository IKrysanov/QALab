import allure
import pytest

from src.async_api_client.models.users import User


@allure.epic("JSONPlaceholder")
@allure.feature("Users")
class TestUsers:
    @allure.title("GET /users возвращает 10 пользователей с полной структурой")
    async def test_list_users_full_schema(self, api_client):
        response = await api_client.users.list()

        users = [User.model_validate(item) for item in response.json()]
        assert len(users) == 10
        # Pydantic уже проверил вложенные структуры (address, company, geo)
        # Если бы хоть один user не имел address.geo.lat — упало бы выше

    @allure.title("Каждый user имеет валидный email и непустой адрес")
    async def test_users_have_valid_emails_and_addresses(self, api_client):
        response = await api_client.users.list()
        users = [User.model_validate(item) for item in response.json()]

        for user in users:
            assert "@" in user.email
            assert user.address.city
            assert user.address.geo.lat
            assert user.address.geo.lng

    @allure.title("GET /users/{id}/posts возвращает 10 постов конкретного пользователя")
    @pytest.mark.parametrize("user_id", [1, 2, 3])
    async def test_user_posts_nested(self, api_client, user_id):
        response = await api_client.users.posts(user_id=user_id)
        posts = response.json()

        assert len(posts) == 10
        assert all(p["userId"] == user_id for p in posts)

    @allure.title("Согласованность: /users/1/posts == /posts?userId=1")
    async def test_nested_endpoint_matches_filtered_list(self, api_client):
        nested = await api_client.users.posts(user_id=1)
        filtered = await api_client.posts.list(user_id=1)

        nested_ids = sorted(p["id"] for p in nested.json())
        filtered_ids = sorted(p["id"] for p in filtered.json())
        assert nested_ids == filtered_ids, (
            "Nested endpoint /users/1/posts should return the same posts as ?userId=1"
        )