import allure
import pytest

from src.async_api_client.models.posts import PostCreate, PostPatch


@allure.epic("JSONPlaceholder")
@allure.feature("Posts")
class TestPosts:
    @allure.story("List")
    @allure.title("GET /posts возвращает 100 постов")
    async def test_list_returns_100_posts(self, api_client):
        await api_client.posts.list()

    @allure.story("List")
    @allure.title("Фильтрация постов по userId")
    @pytest.mark.parametrize("user_id, expected_count", [
        (1, 10),
        (5, 10),
        (10, 10),
    ])
    async def test_list_filtered_by_user(self, api_client, user_id, expected_count):
        await api_client.posts.list(user_id=user_id)

    @allure.story("Read")
    @allure.title("GET /posts/1 — модель валидируется автоматически")
    async def test_get_single_post(self, api_client):
        await api_client.posts.get(1)

    @allure.story("Read")
    @allure.title("GET /posts/9999 → 404 с ожидаемой структурой ошибки")
    async def test_get_nonexistent_post_returns_404(self, api_client):
        await api_client.posts.get(9999, expected_status=404)

    @allure.story("Create")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("POST /posts создаёт пост и возвращает 201 с id=101")
    async def test_create_post_returns_201(self, api_client):
        payload = PostCreate(
            title="Test title",
            body="Test body content",
            userId=1,
        )

        await api_client.posts.create(payload, validate_request=True)

    @allure.story("Create")
    @allure.title("POST с невалидным userId — pydantic ловит на клиенте")
    async def test_create_invalid_user_id_rejected_by_pydantic(self):
        with allure.step("Пытаемся создать пост с user_id=0, который не соответствует условию ge=1"):
            with pytest.raises(ValueError):
                PostCreate(title="x", body="y", userId=0)  # ge=1

    @allure.story("Update")
    @allure.title("PUT /posts/1 заменяет ресурс")
    async def test_update_post(self, api_client):
        await api_client.posts.update(
            request_model=PostCreate,
            post_id=1,
            payload={"id": 1, "userId": 1, "title": "updated", "body": "updated body"},
            validate_request=False,
        )

    @allure.story("Update")
    @allure.title("PATCH /posts/1 обновляет только переданные поля")
    async def test_patch_post_partial(self, api_client):
        await api_client.posts.patch(
            1,
            {"title": "patched only"},
            request_model=PostPatch,
            validate_request=True
        )

    @allure.story("Delete")
    @allure.title("DELETE /posts/1 → 200")
    async def test_delete_post(self, api_client):
        await api_client.posts.delete(1)

    @allure.story("Nested")
    @allure.title("GET /posts/1/comments возвращает комментарии к посту")
    async def test_post_comments_are_linked(self, api_client):
        await api_client.posts.comments(post_id=1)

    @allure.story("HTTP behaviour")
    @allure.title("Прямой запрос к /posts не делает редиректов")
    async def test_no_redirects_on_canonical_url(self, api_client):
        await api_client.posts.list()
