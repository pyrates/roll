from http import HTTPStatus

import pytest

pytestmark = pytest.mark.asyncio


async def test_simple_get_request(client, app):

    @app.route('/test')
    async def get(response):
        response.body = 'test response'

    response = await client.get('/test')
    assert response.status == HTTPStatus.OK
    assert response.body == b'test response'


async def test_simple_non_200_responseonse(client, app):

    @app.route('/test')
    async def get(response):
        response.status = 204

    response = await client.get('/test')
    assert response.status == HTTPStatus.NO_CONTENT
    assert response.body == b''


async def test_not_found_path(client, app):

    @app.route('/test')
    async def get(request, response):
        ...

    response = await client.get('/testing')
    assert response.status == HTTPStatus.NOT_FOUND


async def test_invalid_method(client, app):

    @app.route('/test', methods=['GET'])
    async def get(request, response):
        ...

    response = await client.post('/test', body=b'')
    assert response.status == HTTPStatus.METHOD_NOT_ALLOWED


async def test_post_json(client, app):

    @app.route('/test', methods=['POST'])
    async def post(response, json):
        response.body = json

    response = await client.post('/test', body={'key': 'value'})
    assert response.status == HTTPStatus.OK
    assert response.body == b"{'key': 'value'}"


async def test_post_urlencoded(client, app):

    @app.route('/test', methods=['POST'])
    async def post(response, form):
        response.body = form

    client.content_type = 'application/x-www-form-urlencoded'
    response = await client.post('/test', body={'key': 'value'})
    assert response.status == HTTPStatus.OK
    assert response.body == b"{'key': ['value']}"


async def test_can_define_twice_a_route_with_different_payloads(client, app):

    @app.route('/test', methods=['GET'])
    async def get(response):
        response.body = b'GET'

    @app.route('/test', methods=['POST'])
    async def post(response):
        response.body = b'POST'

    response = await client.get('/test')
    assert response.status == HTTPStatus.OK
    assert response.body == b'GET'

    response = await client.post('/test', {})
    assert response.status == HTTPStatus.OK
    assert response.body == b'POST'
