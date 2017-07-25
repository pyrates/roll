import pytest
from http import HTTPStatus

from roll import HttpError, Response
from roll.extensions import json as json_response

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
            self.response = Response('<h1>Oops.</h1>', self.status)

    @app.route('/test')
    async def get(req):
        raise CustomHttpError(HTTPStatus.INTERNAL_SERVER_ERROR)

    resp = await req('/test')
    assert resp.status == b'500 Internal Server Error'
    assert resp.body == '<h1>Oops.</h1>'


async def test_error_subclasses_without_super(req, app):

    class CustomHttpError(HttpError):
        def __init__(self, code):
            self.response = Response('<h1>Oops.</h1>', code)

    @app.route('/test')
    async def get(req):
        raise CustomHttpError(HTTPStatus.INTERNAL_SERVER_ERROR)

    resp = await req('/test')
    assert resp.status == b'500 Internal Server Error'
    assert resp.body == '<h1>Oops.</h1>'


async def test_error_subclasses_with_json(req, app):

    class JsonHttpError(HttpError):
        def __init__(self, code):
            self.response = json_response(code, message='Oops')

    @app.route('/test')
    async def get(req):
        raise JsonHttpError(HTTPStatus.INTERNAL_SERVER_ERROR)

    resp = await req('/test')
    assert resp.status == b'500 Internal Server Error'
    assert resp.body == '{"message": "Oops"}'


async def test_error_subclasses_incorrect(req, app):

    class IncorrectHttpError(HttpError):
        def __init__(self, code):
            pass

    @app.route('/test')
    async def get(req):
        raise IncorrectHttpError(HTTPStatus.INTERNAL_SERVER_ERROR)

    resp = await req('/test')
    assert resp.status == b'500 Internal Server Error'
    assert resp.body == 'Internal Server Error'
