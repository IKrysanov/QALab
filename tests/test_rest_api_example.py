import pytest
from http import HTTPStatus
import asyncio


from schemas.schemas import schema_image_200


@pytest.mark.parametrize("image_id", ["6euYVVE_u"])
@pytest.mark.dependency()
def test_sync_example_ok(empty_session, image_id):
    """
    Example test function to demonstrate the use of the session_user fixture.
    """

    empty_session.get(
        path=f"/images/{image_id}",
        assert_time=True,
        schema=schema_image_200,
    )

@pytest.mark.parametrize("image_id", ["6euYVVE_u"])
@pytest.mark.asyncio
async def test_async_create_example_ok(async_empty_session, image_id):
    await async_empty_session.get(
        path=f"/images/{image_id}",
        assert_time=True,
        schema=schema_image_200,
    )

@pytest.mark.asyncio
async def test_async_create_many_example(async_empty_session):
    paths = [
        "/images/6euYVVE_u",
        "/images/6euYVVE_u",
        "/images/6euYVVE_u",
        "/images/6euYVVE_u",
        "/images/6euYVVE_u",
        "/images/6euYVVE_u",
        "/images/6euYVVE_u",
        "/images/6euYVVE_u",
        "/images/6euYVVE_u",
        "/images/6euYVVE_u",
        "/images/6euYVVE_u",
        "/images/6euYVVE_u",
        "/images/6euYVVE_u",
        "/images/6euYVVE_u",
    ]

    tasks = [async_empty_session.get(path=path, schema=schema_image_200) for path in paths]

    await asyncio.gather(*tasks)


@pytest.mark.parametrize("breeds_id, expected_status", [("invalid_id", HTTPStatus.BAD_REQUEST)])
@pytest.mark.dependency(depends=["test_example_ok"])
def test_example_fail(empty_session, breeds_id, expected_status):
    empty_session.get(
        path=f"/breeds/{breeds_id}",
        assert_time=True,
        expected_status=expected_status,
        # validator=False,
    )
