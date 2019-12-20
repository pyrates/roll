from http import HTTPStatus

import pytest

from .__main__ import app as app_

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="function")
def app():
    return app_


async def test_stream_from_request_to_response(liveclient, app):
    # Use an iterable so the request will be chunked.
    body = (b"blah" for i in range(100))
    resp = await liveclient.query("POST", "/fullasync", body=body)
    assert resp.status == HTTPStatus.OK
    assert resp.body == b"blah" * 100
    assert resp.chunks is not None
    assert len(resp.chunks) == 100
    for chunk in resp.chunks:
        assert chunk == b"blah"
