from __future__ import annotations
from typing import TYPE_CHECKING

from ..http_client import AsyncHTTPClient

if TYPE_CHECKING:
    from ..client import AsyncAPIClient


class BaseEndpoint:
    def __init__(self, http: AsyncHTTPClient, client: "AsyncAPIClient"):
        self._http = http
        self._client = client