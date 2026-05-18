from typing import Optional

from httpx import Response

from .base import BaseEndpoint
from http import HTTPStatus
from ..http_client import StatusCode

from src.async_api_client.models.posts import Post, PostCreate


class PostsEndpoint(BaseEndpoint):
    PATH = "/posts"

    async def list(
            self,
            user_id: Optional[int] = None,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        params = {"userId": user_id} if user_id is not None else None
        return await self._http.get(
            self.PATH,
            params=params,
            expected_status=expected_status,
        )

    async def get(
            self,
            post_id: int,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        model = Post if expected_status == HTTPStatus.OK else None
        return await self._http.get(
            f"{self.PATH}/{post_id}",
            expected_status=expected_status,
            response_model=model,
        )

    async def create(
            self,
            payload: PostCreate,
            expected_status: StatusCode = HTTPStatus.CREATED,
    ) -> Response:
        model = Post if expected_status == HTTPStatus.CREATED else None
        return await self._http.post(
            self.PATH,
            json=payload.model_dump(by_alias=True),
            expected_status=expected_status,
            response_model=model,
        )

    async def update(
            self,
            post_id: int,
            payload: dict,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        return await self._http.put(
            f"{self.PATH}/{post_id}",
            json=payload,
            expected_status=expected_status,
        )

    async def patch(
            self,
            post_id: int,
            payload: dict,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        return await self._http.patch(
            f"{self.PATH}/{post_id}",
            json=payload,
            expected_status=expected_status,
        )

    async def delete(
            self,
            post_id: int,
            expected_status: StatusCode = HTTPStatus.OK,  # ← у JSONPlaceholder именно HTTPStatus.OK, не 204
    ) -> Response:
        return await self._http.delete(
            f"{self.PATH}/{post_id}",
            expected_status=expected_status,
        )

    async def comments(
            self,
            post_id: int,
            expected_status: StatusCode = HTTPStatus.OK,
    ) -> Response:
        """Вложенный ресурс: /posts/{id}/comments"""

        return await self._http.get(
            f"{self.PATH}/{post_id}/comments",
            expected_status=expected_status,
        )
