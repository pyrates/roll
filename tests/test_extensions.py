import json

import pytest

from roll import extensions

pytestmark = pytest.mark.asyncio


async def test_cors(req,  app):

    extensions.cors(app)

    @app.route('/test')
    async def get(req):
        return 'test response'

    resp = await req('/test')
    assert resp.status == b'200 OK'
    assert resp.body == 'test response'
    assert resp.headers['Access-Control-Allow-Origin'] == '*'


async def test_custom_cors(req, app):

    extensions.cors(app, value='mydomain.org')

    @app.route('/test')
    async def get(req):
        return 'test response'

    resp = await req('/test')
    assert resp.headers['Access-Control-Allow-Origin'] == 'mydomain.org'


async def test_logger(req, app, capsys):

    # startup has yet been called, but logger extensions was not registered
    # yet, so let's simulate a new startup.
    app.hooks['startup'] = []
    extensions.logger(app)
    await app.startup()

    @app.route('/test')
    async def get(req):
        return 'test response'

    await req('/test')
    _, err = capsys.readouterr()
    assert err == 'GET /test\n'


async def test_json_with_default_code(req, app, capsys):

    @app.route('/test')
    async def get(req):
        return extensions.json_response(key='value')

    resp = await req('/test')
    assert resp.headers['Content-Type'] == 'application/json'
    assert json.loads(resp.body) == {'key': 'value'}
    assert resp.status == b'200 OK'


async def test_json_with_custom_code(req, app, capsys):

    @app.route('/test')
    async def get(req):
        return extensions.json_response(400, key='value')

    resp = await req('/test')
    assert resp.headers['Content-Type'] == 'application/json'
    assert json.loads(resp.body) == {'key': 'value'}
    assert resp.status == b'400 Bad Request'
