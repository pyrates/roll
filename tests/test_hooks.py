import pytest

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
