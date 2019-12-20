from http import HTTPStatus

import pytest

from .__main__ import app as app_

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="function")
def app():
    return app_


async def test_hello_view(client, app):
    resp = await client.get("/hello/world")
    assert resp.status == HTTPStatus.OK
    assert resp.body == b"Hello world"
