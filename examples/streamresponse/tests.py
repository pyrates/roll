from http import HTTPStatus

import pytest

from .__main__ import app as app_

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="function")
def app():
    return app_


async def test_cheer_view(client, app):
    resp = await client.get("/cheer")
    assert resp.status == HTTPStatus.OK
    # TODO
    # assert isinstance(resp.body, async_generator)
