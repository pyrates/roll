from http import HTTPStatus

import pytest

pytestmark = pytest.mark.asyncio


async def test_can_set_status_from_numeric_value(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = 202

    resp = await client.get('/test')
    assert resp.status == HTTPStatus.ACCEPTED


async def test_can_set_status_from_httpstatus(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.ACCEPTED

    resp = await client.get('/test')
    assert resp.status == HTTPStatus.ACCEPTED
