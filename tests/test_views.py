import pytest

pytestmark = pytest.mark.asyncio


async def test_simple_get_request(req, app):

    @app.route('/test')
    async def get(req):
        return 'test response'

    resp = await req('/test')
    assert resp.status == b'200 OK'
    assert resp.body == 'test response'


async def test_simple_non_200_response(req, app):

    @app.route('/test')
    async def get(req):
        return b'', 204

    resp = await req('/test')
    assert resp.status == b'204 No Content'
    assert resp.body == b''


async def test_not_found_path(req, app):

    @app.route('/test')
    async def get(req):
        return b''

    resp = await req('/testing')
    assert resp.status == b'404 Not Found'


async def test_invalid_method(req, app):

    @app.route('/test', methods=['GET'])
    async def get(req):
        return b''

    resp = await req('/test', method='POST')
    assert resp.status == b'405 Method Not Allowed'
