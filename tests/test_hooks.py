from http import HTTPStatus
import json

import pytest

from roll import HttpError
from roll.extensions import json_response

pytestmark = pytest.mark.asyncio


async def test_request_hook_can_return_response(req, app):

    @app.listen('request')
    async def listener(request):
        return 'another response', 400

    @app.route('/test')
    async def get(req):
        return 'test response'

    resp = await req('/test')
    assert resp.status == b'400 Bad Request'
    assert resp.body == 'another response'


async def test_response_hook_can_return_response(req, app):

    @app.listen('response')
    async def listener(response, request):
        assert response.body == 'test response'
        return 'another response', 400

    @app.route('/test')
    async def get(req):
        return 'test response'

    resp = await req('/test')
    assert resp.status == b'400 Bad Request'
    assert resp.body == 'another response'


async def test_error_with_json_format(req, app):

    @app.listen('error')
    async def listener(error):
        assert error.message == 'JSON error'
        return json_response(error.status.value,
                             status=error.status,
                             message=error.message)

    @app.route('/test')
    async def get(req):
        raise HttpError(HTTPStatus.INTERNAL_SERVER_ERROR, message='JSON error')

    resp = await req('/test')
    assert resp.status == b'500 Internal Server Error'
    error = json.loads(resp.body)
    assert error == {"status": 500, "message": "JSON error"}
