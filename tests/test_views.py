import pytest

pytestmark = pytest.mark.asyncio


async def test_simple_get_request(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.body = 'test response'

    resp = await client.get('/test')
    assert resp.status == b'200 OK'
    assert resp.body == 'test response'


async def test_simple_non_200_response(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = 204

    resp = await client.get('/test')
    assert resp.status == b'204 No Content'
    assert resp.body == b''


async def test_not_found_path(client, app):

    @app.route('/test')
    async def get(req, resp):
        ...

    resp = await client.get('/testing')
    assert resp.status == b'404 Not Found'


async def test_invalid_method(client, app):

    @app.route('/test', methods=['GET'])
    async def get(req, resp):
        ...

    resp = await client.post('/test', body=b'')
    assert resp.status == b'405 Method Not Allowed'


async def test_options(client, app):

    @app.route('/test')
    async def get(req, resp):
        raise  # Should not be called

    resp = await client.options('/test')
    assert resp.status == b'200 OK'


async def test_post_json(client, app):

    @app.route('/test', methods=['POST'])
    async def get(req, resp):
        resp.body = req.body

    resp = await client.post('/test', body={"key": "value"})
    assert resp.status == b'200 OK'
    assert resp.body == '{"key": "value"}'


async def test_post_urlencoded(client, app):

    @app.route('/test', methods=['POST'])
    async def get(req, resp):
        resp.body = req.body

    client.content_type = 'application/x-www-form-urlencoded'
    resp = await client.post('/test', body={"key": "value"})
    assert resp.status == b'200 OK'
    assert resp.body == 'key=value'
