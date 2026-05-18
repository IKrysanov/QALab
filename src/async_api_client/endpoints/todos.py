from typing import Optional, Any
from httpx import Response

from .base import BaseEndpoint

from http import HTTPStatus
from ..http_client import StatusCode

from src.async_api_client.models.todos import Todo


class TodosEndpoint(BaseEndpoint):
    PATH = "/todos"

    async def list(
        self,
        user_id: Optional[int] = None,
        completed: Optional[bool] = None,
        expected_status: StatusCode = HTTPStatus.OK,
        **kwargs: Any
    ) -> Response:
        params: dict = {}
        if user_id is not None:
            params["userId"] = user_id
        if completed is not None:
            params["completed"] = str(completed).lower()
        return await self._http.get(
            self.PATH,
            params=params or None,
            expected_status=expected_status,
            **kwargs,
        )

    async def get(self, todo_id: int, expected_status: StatusCode = HTTPStatus.OK) -> Response:
        model = Todo if expected_status == HTTPStatus.OK else None
        return await self._http.get(
            f"{self.PATH}/{todo_id}",
            expected_status=expected_status,
            response_model=model,
        )