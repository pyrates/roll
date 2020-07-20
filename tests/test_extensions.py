import json
from http import HTTPStatus
from pathlib import Path

import pytest
from roll import extensions

pytestmark = pytest.mark.asyncio


async def test_cors(client, app):

    extensions.cors(app)

    @app.route('/test')
    async def get(req, resp):
        resp.body = 'test response'

    resp = await client.get('/test')
    assert resp.status == HTTPStatus.OK
    assert resp.body == b'test response'
    assert resp.headers['Access-Control-Allow-Origin'] == '*'


async def test_custom_cors_origin(client, app):

    extensions.cors(app, origin='mydomain.org')

    @app.route('/test')
    async def get(req, resp):
        resp.body = 'test response'

    resp = await client.get('/test')
    assert resp.headers['Access-Control-Allow-Origin'] == 'mydomain.org'
    assert 'Access-Control-Allow-Methods' not in resp.headers
    assert 'Access-Control-Allow-Credentials' not in resp.headers


async def test_custom_cors_methods(client, app):

    extensions.cors(app, methods=['PATCH', 'PUT'])

    @app.route('/test')
    async def get(req, resp):
        resp.body = 'test response'

    resp = await client.get('/test')
    assert resp.headers['Access-Control-Allow-Methods'] == 'PATCH,PUT'


async def test_wildcard_cors_methods(client, app):

    extensions.cors(app, methods='*')

    resp = await client.get('/test')
    assert (resp.headers['Access-Control-Allow-Methods'] ==
            ','.join(extensions.HTTP_METHODS))


async def test_custom_cors_headers(client, app):

    extensions.cors(app, headers=['X-Powered-By', 'X-Requested-With'])

    @app.route('/test')
    async def get(req, resp):
        resp.body = 'test response'

    resp = await client.get('/test')
    assert (resp.headers['Access-Control-Allow-Headers'] ==
            'X-Powered-By,X-Requested-With')


async def test_cors_credentials(client, app):

    extensions.cors(app, credentials=True)

    @app.route('/test')
    async def get(req, resp):
        resp.body = 'test response'

    resp = await client.get('/test')
    assert resp.headers['Access-Control-Allow-Credentials'] == "true"


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
    assert resp.headers['Content-Type'] == 'application/json; charset=utf-8'
    assert json.loads(resp.body.decode()) == {'key': 'value'}
    assert resp.status == HTTPStatus.OK


async def test_json_with_custom_code(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.json = {'key': 'value'}
        resp.status = 400

    resp = await client.get('/test')
    assert resp.headers['Content-Type'] == 'application/json; charset=utf-8'
    assert json.loads(resp.body.decode()) == {'key': 'value'}
    assert resp.status == HTTPStatus.BAD_REQUEST


async def test_traceback(client, app, capsys):

    extensions.traceback(app)

    @app.route('/test')
    async def get(req, resp):
        raise ValueError('Unhandled exception')

    resp = await client.get('/test')
    _, err = capsys.readouterr()
    assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert 'Unhandled exception' in err


async def test_options(client, app):

    extensions.options(app)

    @app.route('/test')
    async def get(req, resp):
        raise  # Should not be called.

    resp = await client.options('/test')
    assert resp.status == HTTPStatus.OK


async def test_static(client, app):

    # startup has yet been called, but static extensions was not registered
    # yet, so let's simulate a new startup.
    app.hooks['startup'] = []
    extensions.static(app, root=Path(__file__).parent / 'static')
    url_for = extensions.named_url(app)
    await app.startup()

    resp = await client.get('/static/index.html')
    assert resp.status == HTTPStatus.OK
    assert b'Test' in resp.body
    assert resp.headers['Content-Type'] == 'text/html'

    resp = await client.get('/static/sub/index.html')
    assert resp.status == HTTPStatus.OK
    assert b'Subtest' in resp.body
    assert resp.headers['Content-Type'] == 'text/html'

    resp = await client.get('/static/style.css')
    assert resp.status == HTTPStatus.OK
    assert b'chocolate' in resp.body
    assert resp.headers['Content-Type'] == 'text/css'

    assert url_for("static", path="path/myfile.png") == "/static/path/myfile.png"


async def test_static_with_default_index(client, app):

    app.hooks['startup'] = []
    extensions.static(app, root=Path(__file__).parent / 'static',
                      default_index='index.html')
    await app.startup()

    resp = await client.get('/static/index.html')
    assert resp.status == HTTPStatus.OK
    assert b'Test' in resp.body
    assert resp.headers['Content-Type'] == 'text/html'

    resp = await client.get('/static/')
    assert resp.status == HTTPStatus.OK
    assert b'Test' in resp.body
    assert resp.headers['Content-Type'] == 'text/html'

    resp = await client.get('/static/sub/index.html')
    assert resp.status == HTTPStatus.OK
    assert b'Subtest' in resp.body
    assert resp.headers['Content-Type'] == 'text/html'

    resp = await client.get('/static/sub/')
    assert resp.status == HTTPStatus.OK
    assert b'Subtest' in resp.body
    assert resp.headers['Content-Type'] == 'text/html'


async def test_static_raises_if_path_is_outside_root(client, app):

    app.hooks['startup'] = []
    extensions.static(app, root=Path(__file__).parent / 'static')
    await app.startup()

    resp = await client.get('/static/../../README.md')
    assert resp.status == HTTPStatus.BAD_REQUEST


async def test_can_change_static_prefix(client, app):

    app.hooks['startup'] = []
    extensions.static(app, root=Path(__file__).parent / 'static',
                      prefix='/foo')
    await app.startup()

    resp = await client.get('/foo/index.html')
    assert resp.status == HTTPStatus.OK
    assert b'Test' in resp.body


async def test_get_accept_content_negociation(client, app):

    extensions.content_negociation(app)

    @app.route('/test', accepts=['text/html'])
    async def get(req, resp):
        resp.headers['Content-Type'] = 'text/html'
        resp.body = 'accepted'

    resp = await client.get('/test', headers={'Accept': 'text/html'})
    assert resp.status == HTTPStatus.OK
    assert resp.body == b'accepted'
    assert resp.headers['Content-Type'] == 'text/html'


async def test_get_accept_content_negociation_if_many(client, app):

    extensions.content_negociation(app)

    @app.route('/test', accepts=['text/html', 'application/json'])
    async def get(req, resp):
        if req.headers['ACCEPT'] == 'text/html':
            resp.headers['Content-Type'] = 'text/html'
            resp.body = '<h1>accepted</h1>'
        elif req.headers['ACCEPT'] == 'application/json':
            resp.json = {'status': 'accepted'}

    resp = await client.get('/test', headers={'Accept': 'text/html'})
    assert resp.status == HTTPStatus.OK
    assert resp.body == b'<h1>accepted</h1>'
    assert resp.headers['Content-Type'] == 'text/html'
    resp = await client.get('/test', headers={'Accept': 'application/json'})
    assert resp.status == HTTPStatus.OK
    assert json.loads(resp.body.decode()) == {'status': 'accepted'}
    assert resp.headers['Content-Type'] == 'application/json; charset=utf-8'


async def test_get_reject_content_negociation(client, app):

    extensions.content_negociation(app)

    @app.route('/test', accepts=['text/html'])
    async def get(req, resp):
        resp.body = 'rejected'

    resp = await client.get('/test', headers={'Accept': 'text/css'})
    assert resp.status == HTTPStatus.NOT_ACCEPTABLE


async def test_get_reject_content_negociation_if_no_accept_header(client, app):

    extensions.content_negociation(app)

    @app.route('/test', accepts=['*/*'])
    async def get(req, resp):
        resp.body = 'rejected'

    resp = await client.get('/test')
    assert resp.status == HTTPStatus.NOT_ACCEPTABLE


async def test_get_accept_star_content_negociation(client, app):

    extensions.content_negociation(app)

    @app.route('/test', accepts=['text/css'])
    async def get(req, resp):
        resp.body = 'accepted'

    resp = await client.get('/test', headers={'Accept': 'text/*'})
    assert resp.status == HTTPStatus.OK


async def test_post_accept_content_negociation(client, app):

    extensions.content_negociation(app)

    @app.route('/test', methods=['POST'], accepts=['application/json'])
    async def get(req, resp):
        resp.json = {'status': 'accepted'}

    client.content_type = 'application/x-www-form-urlencoded'
    resp = await client.post('/test', body={'key': 'value'},
                             headers={'Accept': 'application/json'})
    assert resp.status == HTTPStatus.OK
    assert resp.headers['Content-Type'] == 'application/json; charset=utf-8'
    assert json.loads(resp.body.decode()) == {'status': 'accepted'}


async def test_post_reject_content_negociation(client, app):

    extensions.content_negociation(app)

    @app.route('/test', methods=['POST'], accepts=['text/html'])
    async def get(req, resp):
        resp.json = {'status': 'accepted'}

    client.content_type = 'application/x-www-form-urlencoded'
    resp = await client.post('/test', body={'key': 'value'},
                             headers={'Accept': 'application/json'})
    assert resp.status == HTTPStatus.NOT_ACCEPTABLE


async def test_can_call_static_twice(client, app):

    # startup has yet been called, but static extensions was not registered
    # yet, so let's simulate a new startup.
    app.hooks["startup"] = []
    extensions.static(
        app, root=Path(__file__).parent / "static", prefix="/static/", name="statics"
    )
    extensions.static(
        app, root=Path(__file__).parent / "medias", prefix="/medias/", name="medias"
    )
    url_for = extensions.named_url(app)
    await app.startup()
    assert url_for("statics", path="myfile.png") == "/static/myfile.png"
    assert url_for("medias", path="myfile.mp3") == "/medias/myfile.mp3"
