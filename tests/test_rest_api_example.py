import pytest
from http import HTTPStatus


from schemas.schemas import schema_image_200


@pytest.mark.parametrize("image_id", ["6euYVVE_u"])
@pytest.mark.dependency()
def test_example_ok(empty_session, image_id):
    """
    Example test function to demonstrate the use of the session_user fixture.
    """

    empty_session.get(
        path=f"/images/{image_id}",
        assert_time=True,
        schema=schema_image_200,
    )


@pytest.mark.parametrize("breeds_id, expected_status", [("invalid_id", HTTPStatus.BAD_REQUEST)])
@pytest.mark.dependency(depends=["test_example_ok"])
def test_example_fail(empty_session, breeds_id, expected_status):
    empty_session.get(
        path=f"/breeds/{breeds_id}",
        assert_time=True,
        expected_status=expected_status,
        # validator=False,
    )
