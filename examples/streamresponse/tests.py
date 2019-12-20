from http import HTTPStatus

import pytest

from .__main__ import app as app_

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="function")
def app():
    return app_


async def test_cheer_view(liveclient, app):
    resp, content = await liveclient.query("GET", "/cheer")
    assert resp.status == HTTPStatus.OK
