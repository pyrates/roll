from http import HTTPStatus
import json

import pytest

from roll import HttpError
from roll.extensions import json_response

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
    assert resp.status == b'400 Bad Request'
    assert resp.body == 'another response'


async def test_response_hook_can_alter_response(client, app):

    @app.listen('response')
    async def listener(response, request):
        assert response.body == 'test response'
        response.body = 'another response'
        response.status = 400

    @app.route('/test')
    async def get(req, resp):
        resp.body = 'test response'

    resp = await client.get('/test')
    assert resp.status == b'400 Bad Request'
    assert resp.body == 'another response'


async def test_error_with_json_format(client, app):

    @app.listen('error')
    async def listener(error, response):
        assert error.message == 'JSON error'
        json_response(response, error.status.value, status=error.status,
                      message=error.message)

    @app.route('/test')
    async def get(req, resp):
        raise HttpError(HTTPStatus.INTERNAL_SERVER_ERROR, message='JSON error')

    resp = await client.get('/test')
    assert resp.status == b'500 Internal Server Error'
    error = json.loads(resp.body)
    assert error == {"status": 500, "message": "JSON error"}
