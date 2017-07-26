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


async def test_error_only_with_status(req, app):

    @app.route('/test')
    async def get(req):
        raise HttpError(500)

    resp = await req('/test')
    assert resp.status == b'500 Internal Server Error'
    assert resp.body == 'Internal Server Error'


async def test_error_only_with_httpstatus(req, app):

    @app.route('/test')
    async def get(req):
        raise HttpError(HTTPStatus.INTERNAL_SERVER_ERROR)

    resp = await req('/test')
    assert resp.status == b'500 Internal Server Error'
    assert resp.body == 'Internal Server Error'


async def test_error_subclasses_with_super(req, app):

    class CustomHttpError(HttpError):
        def __init__(self, code):
            super().__init__(code)
            self.message = '<h1>Oops.</h1>'

    @app.route('/test')
    async def get(req):
        raise CustomHttpError(HTTPStatus.INTERNAL_SERVER_ERROR)

    resp = await req('/test')
    assert resp.status == b'500 Internal Server Error'
    assert resp.body == '<h1>Oops.</h1>'


async def test_error_subclasses_without_super(req, app):

    class CustomHttpError(HttpError):
        def __init__(self, code):
            self.status = HTTPStatus(code)
            self.message = '<h1>Oops.</h1>'

    @app.route('/test')
    async def get(req):
        raise CustomHttpError(HTTPStatus.INTERNAL_SERVER_ERROR)

    resp = await req('/test')
    assert resp.status == b'500 Internal Server Error'
    assert resp.body == '<h1>Oops.</h1>'
