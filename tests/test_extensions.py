import json

import pytest

from roll import extensions

pytestmark = pytest.mark.asyncio


async def test_cors(client, app):

    extensions.cors(app)

    @app.route('/test')
    async def get(req, resp):
        resp.body = 'test response'

    resp = await client.get('/test')
    assert resp.status == b'200 OK'
    assert resp.body == 'test response'
    assert resp.headers['Access-Control-Allow-Origin'] == '*'


async def test_custom_cors(client, app):

    extensions.cors(app, value='mydomain.org')

    @app.route('/test')
    async def get(req, resp):
        resp.body = 'test response'

    resp = await client.get('/test')
    assert resp.headers['Access-Control-Allow-Origin'] == 'mydomain.org'


async def test_logger(client, app, capsys):

    # startup has yet been called, but logger extensions was not registered
    # yet, so let's simulate a new startup.
    app.hooks['startup'] = []
    extensions.logger(app)
    await app.startup()

    @app.route('/test')
    async def get(req, resp):
        return 'test response'

    await client.get('/test')
    _, err = capsys.readouterr()
    assert err == 'GET /test\n'


async def test_json_with_default_code(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.json = {'key': 'value'}

    resp = await client.get('/test')
    assert resp.headers['Content-Type'] == 'application/json'
    assert json.loads(resp.body) == {'key': 'value'}
    assert resp.status == b'200 OK'


async def test_json_with_custom_code(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.json = {'key': 'value'}
        resp.status = 400

    resp = await client.get('/test')
    assert resp.headers['Content-Type'] == 'application/json'
    assert json.loads(resp.body) == {'key': 'value'}
    assert resp.status == b'400 Bad Request'


async def test_traceback(client, app, capsys):

    extensions.traceback(app)

    @app.route('/test')
    async def get(req, resp):
        raise ValueError('Unhandled exception')

    resp = await client.get('/test')
    _, err = capsys.readouterr()
    assert resp.status == b'500 Internal Server Error'
    assert 'Unhandled exception' in err


async def test_options(client, app):

    @app.route('/test')
    async def get(req, resp):
        raise  # Should not be called.

    resp = await client.options('/test')
    assert resp.status == b'200 OK'
