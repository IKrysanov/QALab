import allure
import pytest

from src.async_api_client.models.posts import Post, PostCreate, PostPatch, Comment
from src.async_api_client.asserts import (
    assert_status_code,
    assert_no_redirects,
    assert_response_time_below,
)


@allure.epic("JSONPlaceholder")
@allure.feature("Posts")
class TestPosts:
    @allure.story("List")
    @allure.title("GET /posts возвращает 100 постов")
    async def test_list_returns_100_posts(self, api_client):
        response = await api_client.posts.list()

        posts = [Post.model_validate(item) for item in response.json()]
        assert len(posts) == 100
        assert_response_time_below(response, ms=3000)

    @allure.story("List")
    @allure.title("Фильтрация постов по userId")
    @pytest.mark.parametrize("user_id, expected_count", [
        (1, 10),
        (5, 10),
        (10, 10),
    ])
    async def test_list_filtered_by_user(self, api_client, user_id, expected_count):
        response = await api_client.posts.list(user_id=user_id)

        posts = [Post.model_validate(item) for item in response.json()]
        assert len(posts) == expected_count
        assert all(p.user_id == user_id for p in posts), (
            f"Some posts belong to other users: {[p.user_id for p in posts]}"
        )

    @allure.story("Read")
    @allure.title("GET /posts/1 — модель валидируется автоматически")
    async def test_get_single_post(self, api_client):
        # response_model=Post подключается внутри endpoint.get() — валидация автоматом
        response = await api_client.posts.get(1)

        post = Post.model_validate(response.json())
        assert post.id == 1
        assert post.user_id == 1
        assert post.title  # non-empty
        assert post.body

    @allure.story("Read")
    @allure.title("GET /posts/9999 → 404 с ожидаемой структурой ошибки")
    async def test_get_nonexistent_post_returns_404(self, api_client):
        response = await api_client.posts.get(9999, expected_status=404)
        assert_status_code(response, 404)
        assert response.json() == {}

    @allure.story("Create")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("POST /posts создаёт пост и возвращает 201 с id=101")
    async def test_create_post_returns_201(self, api_client):
        payload =  PostCreate(
            title="Test title",
            body="Test body content",
            userId=1,
        )

        # {"title": "Test title", "body": "Test body content", "userId": 1}

        response = await api_client.posts.create(payload, validate_request=True)

        # На фейковом API всегда id=101 для нового объекта
        created = response.json()
        assert created.get("id") == 101
        assert created.get("title") == "Test title"
        assert created.get("userId") == 1

    @allure.story("Create")
    @allure.title("POST с невалидным userId — pydantic ловит на клиенте")
    async def test_create_invalid_user_id_rejected_by_pydantic(self):
        with allure.step("Пытаемся создать пост с user_id=0, который не соответствует условию ge=1"):
            with pytest.raises(ValueError):
                PostCreate(title="x", body="y", userId=0)  # ge=1

    @allure.story("Update")
    @allure.title("PUT /posts/1 заменяет ресурс")
    async def test_update_post(self, api_client):
        response = await api_client.posts.update(
            # request_model=PostCreate,
            post_id=1,
            payload={"id": 1, "userId": 1, "title": "updated", "body": "updated body"},
            validate_request=False,
        )

        body = response.json()
        assert body["id"] == 1
        assert body["title"] == "updated"

    @allure.story("Update")
    @allure.title("PATCH /posts/1 обновляет только переданные поля")
    async def test_patch_post_partial(self, api_client):
        response = await api_client.posts.patch(
            1,
            {"title": "patched only"},
            request_model=PostPatch,
            validate_request=True
        )

        body = response.json()
        assert body["title"] == "patched only"
        # Остальные поля сервер вернёт неизменными
        assert "userId" in body
        assert "body" in body

    @allure.story("Delete")
    @allure.title("DELETE /posts/1 → 200")
    async def test_delete_post(self, api_client):
        response = await api_client.posts.delete(1)
        assert response.status_code == 200

    @allure.story("Nested")
    @allure.title("GET /posts/1/comments возвращает комментарии к посту")
    async def test_post_comments_are_linked(self, api_client):
        response = await api_client.posts.comments(post_id=1)

        comments = [Comment.model_validate(item) for item in response.json()]
        assert len(comments) > 0
        assert all(c.post_id == 1 for c in comments), (
            "Some comments belong to other posts"
        )

    @allure.story("HTTP behaviour")
    @allure.title("Прямой запрос к /posts не делает редиректов")
    async def test_no_redirects_on_canonical_url(self, api_client):
        response = await api_client.posts.list()
        assert_no_redirects(response)
