from http import HTTPStatus

import pytest

from .__main__ import app as app_

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="function")
def app():
    return app_


async def test_cheer_view(liveclient, app):
    resp = await liveclient.query("GET", "/cheer")
    assert resp.status == HTTPStatus.OK
    assert resp.chunks is not None
    assert len(resp.chunks) == 109
    assert len(resp.chunks[0]) == 4096
    assert sum(len(chunk) for chunk in resp.chunks) == 443926
