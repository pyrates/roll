import pytest
from http import HTTPStatus

from roll import HttpError

pytestmark = pytest.mark.asyncio


async def test_simple_error(req, app):

    @app.route('/test')
    async def get(req):
        raise HttpError(500, 'Oops.')

    resp = await req('/test')
    assert resp.status == b'500 Internal Server Error'
    assert resp.body == 'Oops.'


async def test_httpstatus_error(req, app):

    @app.route('/test')
    async def get(req):
        raise HttpError(HTTPStatus.BAD_REQUEST, 'Really bad.')

    resp = await req('/test')
    assert resp.status == b'400 Bad Request'
    assert resp.body == 'Really bad.'


async def test_error_only_with_httpstatus(req, app):

    @app.route('/test')
    async def get(req):
        raise HttpError(HTTPStatus.INTERNAL_SERVER_ERROR)

    resp = await req('/test')
    assert resp.status == b'500 Internal Server Error'
    assert resp.body == 'Internal Server Error'
