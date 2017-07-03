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

    extensions.logger(app)

    @app.route('/test')
    async def get(req):
        return 'test response'

    await req('/test')
    _, err = capsys.readouterr()
    assert err == 'GET /test\n'


async def test_json_with_default_code(req, app, capsys):

    extensions.logger(app)

    @app.route('/test')
    async def get(req):
        return extensions.json(key='value')

    resp = await req('/test')
    assert resp.headers['Content-Type'] == 'application/json'
    assert json.loads(resp.body) == {'key': 'value'}
    assert resp.status == b'200 OK'


async def test_json_with_custom_code(req, app, capsys):

    extensions.logger(app)

    @app.route('/test')
    async def get(req):
        return extensions.json(400, key='value')

    resp = await req('/test')
    assert resp.headers['Content-Type'] == 'application/json'
    assert json.loads(resp.body) == {'key': 'value'}
    assert resp.status == b'400 Bad Request'
