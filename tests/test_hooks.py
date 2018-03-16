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
    assert resp.body == 'another response'


async def test_error_with_json_format(client, app):

    @app.listen('error')
    async def listener(request, response, error):
        assert error.message == b'JSON error'
        response.json = {
            'status': error.status, 'message': error.message.decode()}

    @app.route('/test')
    async def get(req, resp):
        raise HttpError(HTTPStatus.INTERNAL_SERVER_ERROR, message='JSON error')

    resp = await client.get('/test')
    assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR
    error = json.loads(resp.body)
    assert error == {"status": 500, "message": "JSON error"}


async def test_third_parties_can_call_hook_their_way(client, app):

    @app.listen('custom')
    async def listener(myarg):
        return myarg

    assert await app.hook('custom', myarg='kwarg') == 'kwarg'
    assert await app.hook('custom', 'arg') == 'arg'


async def test_request_hook_is_called_even_if_path_is_not_found(client, app):

    @app.listen('request')
    async def listener(request, response):
        if not request.route.payload:
            response.status = 400
            response.body = b'Really this is a bad request'
            return True  # Shortcuts the response process.

    resp = await client.get('/not-found')
    assert resp.status == HTTPStatus.BAD_REQUEST
    assert resp.body == b'Really this is a bad request'
