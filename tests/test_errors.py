import pytest
from http import HTTPStatus

from roll import HttpError

pytestmark = pytest.mark.asyncio


async def test_simple_error(client, app):

    @app.route('/test')
    async def get(req, resp):
        raise HttpError(500, 'Oops.')

    resp = await client.get('/test')
    assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert resp.body == 'Oops.'


async def test_httpstatus_error(client, app):

    @app.route('/test')
    async def get(req, resp):
        raise HttpError(HTTPStatus.BAD_REQUEST, 'Really bad.')

    resp = await client.get('/test')
    assert resp.status == HTTPStatus.BAD_REQUEST
    assert resp.body == 'Really bad.'


async def test_error_only_with_status(client, app):

    @app.route('/test')
    async def get(req, resp):
        raise HttpError(500)

    resp = await client.get('/test')
    assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert resp.body == 'Internal Server Error'


async def test_error_only_with_httpstatus(client, app):

    @app.route('/test')
    async def get(req, resp):
        raise HttpError(HTTPStatus.INTERNAL_SERVER_ERROR)

    resp = await client.get('/test')
    assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert resp.body == 'Internal Server Error'


async def test_error_subclasses_with_super(client, app):

    class CustomHttpError(HttpError):
        def __init__(self, code):
            super().__init__(code)
            self.message = '<h1>Oops.</h1>'

    @app.route('/test')
    async def get(req, resp):
        raise CustomHttpError(HTTPStatus.INTERNAL_SERVER_ERROR)

    resp = await client.get('/test')
    assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert resp.body == '<h1>Oops.</h1>'


async def test_error_subclasses_without_super(client, app):

    class CustomHttpError(HttpError):
        def __init__(self, code):
            self.status = HTTPStatus(code)
            self.message = '<h1>Oops.</h1>'

    @app.route('/test')
    async def get(req, resp):
        raise CustomHttpError(HTTPStatus.INTERNAL_SERVER_ERROR)

    resp = await client.get('/test')
    assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert resp.body == '<h1>Oops.</h1>'
