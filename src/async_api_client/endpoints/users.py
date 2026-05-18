from httpx import Response

from .base import BaseEndpoint

from http import HTTPStatus
from ..http_client import StatusCode

from src.async_api_client.models.users import User


class UsersEndpoint(BaseEndpoint):
    PATH = "/users"

    async def list(self, expected_status: StatusCode = HTTPStatus.OK) -> Response:
        return await self._http.get(self.PATH, expected_status=expected_status)

    async def get(self, user_id: int, expected_status: StatusCode = HTTPStatus.OK) -> Response:
        model = User if expected_status == HTTPStatus.OK else None
        return await self._http.get(
            f"{self.PATH}/{user_id}",
            expected_status=expected_status,
            response_model=model,
        )

    async def posts(self, user_id: int, expected_status: StatusCode = HTTPStatus.OK) -> Response:
        return await self._http.get(
            f"{self.PATH}/{user_id}/posts",
            expected_status=expected_status,
        )

    async def todos(self, user_id: int, expected_status: StatusCode = HTTPStatus.OK) -> Response:
        return await self._http.get(
            f"{self.PATH}/{user_id}/todos",
            expected_status=expected_status,
        )

    async def albums(self, user_id: int, expected_status: StatusCode = HTTPStatus.OK) -> Response:
        return await self._http.get(
            f"{self.PATH}/{user_id}/albums",
            expected_status=expected_status,
        )
