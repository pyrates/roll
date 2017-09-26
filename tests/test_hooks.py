from http import HTTPStatus
import json

import pytest

from roll import HttpError

pytestmark = pytest.mark.asyncio


async def test_request_hook_can_alter_response(client, app):

    @app.listen('request')
    async def listener(request, response):
        response.status = 400
        response.body = 'another response'
        return True  # Shortcut the response process.

    @app.route('/test')
    async def get(req, resp):
        resp.body = 'test response'

    resp = await client.get('/test')
    assert resp.status == HTTPStatus.BAD_REQUEST
    assert resp.body == 'another response'


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
        assert error.message == 'JSON error'
        response.json = {'status': error.status, 'message': error.message}

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
