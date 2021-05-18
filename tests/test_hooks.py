from http import HTTPStatus
import json

import pytest

from roll import HttpError

pytestmark = pytest.mark.asyncio


async def test_request_hook_can_alter_response(client, app):

    @app.listen('request')
    async def listener(request, response):
        response.status = 400
        response.body = b'another response'
        return True  # Shortcut the response process.

    @app.route('/test')
    async def get(req, resp):
        resp.body = 'test response'

    resp = await client.get('/test')
    assert resp.status == HTTPStatus.BAD_REQUEST
    assert resp.body == b'another response'


async def test_response_hook_can_alter_response(client, app):

    @app.listen('response')
    async def listener(request, response):
        assert response.body == 'test response'
        response.body = 'another response'
        response.status = 400

    @app.route('/test')
    async def get(req, resp):
        resp.body = 'test response'

    resp = await client.get('/test')
    assert resp.status == HTTPStatus.BAD_REQUEST
    assert resp.body == b'another response'


async def test_error_with_json_format(client, app):

    @app.listen('error')
    async def listener(request, response, error):
        assert error.message == 'JSON error'
        response.json = {'status': error.status, 'message': error.message}

    @app.route('/test')
    async def get(req, resp):
        raise HttpError(HTTPStatus.INTERNAL_SERVER_ERROR, message='JSON error')

    resp = await client.get('/test')
    assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR
    error = json.loads(resp.body.decode())
    assert error == {"status": 500, "message": "JSON error"}


async def test_third_parties_can_call_hook_their_way(client, app):

    @app.listen('custom')
    async def listener(myarg):
        return myarg

    assert await app.hook('custom', myarg='kwarg') == 'kwarg'
    assert await app.hook('custom', 'arg') == 'arg'


async def test_headers_hook_is_called_even_if_path_is_not_found(client, app):

    @app.listen('headers')
    async def listener(request, response):
        if not request.route.payload:
            response.status = 400
            response.body = b'Really this is a bad request'
            return True  # Shortcuts the response process.

    resp = await client.get('/not-found')
    assert resp.status == HTTPStatus.BAD_REQUEST
    assert resp.body == b'Really this is a bad request'


async def test_headers_hook_cannot_consume_request_body(client, app):

    @app.listen('headers')
    async def listener(request, response):
        if not request.route.payload:
            try:
                request.body
            except HttpError:
                response.status = 200
                response.body = b'raised as expected'
                return True  # Shortcuts the response process.

    resp = await client.get('/not-found')
    assert resp.status == HTTPStatus.OK
    assert resp.body == b'raised as expected'


async def test_headers_hook_can_consume_request_body_explicitly(client, app):

    @app.listen('headers')
    async def listener(request, response):
        response.status = 200
        response.body = await request.read()
        return True  # Shortcuts the response process.

    resp = await client.post('/test', "blah")
    assert resp.status == HTTPStatus.OK
    assert resp.body == b'blah'


async def test_request_hook_can_consume_request_body(client, app):

    @app.route('/test', methods=["POST"])
    async def get(req, resp):
        pass

    @app.listen('request')
    async def listener(request, response):
        response.status = 200
        response.body = request.body
        return True  # Shortcuts the response process.

    resp = await client.post('/test', "blah")
    assert resp.status == HTTPStatus.OK
    assert resp.body == b'blah'


async def test_can_retrieve_original_error_on_error_hook(client, app):
    original_error = None

    @app.listen('error')
    async def listener(request, response, error):
        nonlocal original_error
        original_error = error.__context__

    @app.route('/raise')
    async def handler(request, response):
        raise ValueError("Custom Error Message")

    resp = await client.get('/raise')
    assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert resp.body == b'Custom Error Message'
    assert isinstance(original_error, ValueError)
