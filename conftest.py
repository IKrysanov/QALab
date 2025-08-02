import pytest
from dotenv import load_dotenv

from src.http_client import APIClient
from dotenv import load_dotenv
import os

from requests.auth import HTTPBasicAuth

load_dotenv()


@pytest.fixture(scope="module")
def session_user():
    """Fixture to create a session for the user."""

    with APIClient() as api:
        yield api


@pytest.fixture(scope="module")
def session_admin():
    """Fixture to create a session for the admin."""

    with APIClient() as api:
        api.session.auth = HTTPBasicAuth(
            os.getenv("USERNAME_ADMIN"), os.getenv("PASSWORD_ADMIN")
        )
        yield api


@pytest.fixture(scope="module")
def empty_session():
    """Fixture to create an empty session."""

    with APIClient(headers={"x-api-key": os.getenv("API_KEY")}) as api:
        yield api


@pytest.fixture(scope="module")
def user(session_user):
    """Fixture to authenticate a user session."""

    session_user.post("/auth/login", json={
        "username": os.getenv("USERNAME_USER"),
        "password": os.getenv("PASSWORD_USER"),
    })

    return session_user
