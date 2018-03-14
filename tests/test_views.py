from http import HTTPStatus

import pytest

pytestmark = pytest.mark.asyncio


async def test_simple_get_request(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.body = 'test response'

    resp = await client.get('/test')
    assert resp.status == HTTPStatus.OK
    assert resp.body == 'test response'


async def test_simple_non_200_response(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = 204

    resp = await client.get('/test')
    assert resp.status == HTTPStatus.NO_CONTENT
    assert resp.body == b''


async def test_not_found_path(client, app):

    @app.route('/test')
    async def get(req, resp):
        ...

    resp = await client.get('/testing')
    assert resp.status == HTTPStatus.NOT_FOUND


async def test_invalid_method(client, app):

    @app.route('/test', methods=['GET'])
    async def get(req, resp):
        ...

    resp = await client.post('/test', body=b'')
    assert resp.status == HTTPStatus.METHOD_NOT_ALLOWED


async def test_post_json(client, app):

    @app.route('/test', methods=['POST'])
    async def post(req, resp):
        resp.body = req.body

    resp = await client.post('/test', body={'key': 'value'})
    assert resp.status == HTTPStatus.OK
    assert resp.body == b'{"key": "value"}'


async def test_post_urlencoded(client, app):

    @app.route('/test', methods=['POST'])
    async def post(req, resp):
        resp.body = req.body

    client.content_type = 'application/x-www-form-urlencoded'
    resp = await client.post('/test', body={'key': 'value'})
    assert resp.status == HTTPStatus.OK
    assert resp.body == b'key=value'


async def test_can_define_twice_a_route_with_different_payloads(client, app):

    @app.route('/test', methods=['GET'])
    async def get(req, resp):
        resp.body = b'GET'

    @app.route('/test', methods=['POST'])
    async def post(req, resp):
        resp.body = b'POST'

    resp = await client.get('/test')
    assert resp.status == HTTPStatus.OK
    assert resp.body == b'GET'

    resp = await client.post('/test', {})
    assert resp.status == HTTPStatus.OK
    assert resp.body == b'POST'
