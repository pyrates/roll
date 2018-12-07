import json
from pathlib import Path
from http import HTTPStatus

import pytest
from roll import extensions

pytestmark = pytest.mark.asyncio


async def test_cors(client, app):

    extensions.cors(app)

    @app.route('/test')
    async def get(request, response):
        response.body = 'test response'

    response = await client.get('/test')
    assert response.status == HTTPStatus.OK
    assert response.body == b'test response'
    assert response.headers['Access-Control-Allow-Origin'] == '*'


async def test_custom_cors_origin(client, app):

    extensions.cors(app, origin='mydomain.org')

    @app.route('/test')
    async def get(request, response):
        response.body = 'test response'

    response = await client.get('/test')
    assert response.headers['Access-Control-Allow-Origin'] == 'mydomain.org'
    assert 'Access-Control-Allow-Methods' not in response.headers


async def test_custom_cors_methods(client, app):

    extensions.cors(app, methods=['PATCH', 'PUT'])

    @app.route('/test')
    async def get(request, response):
        response.body = 'test response'

    response = await client.get('/test')
    assert response.headers['Access-Control-Allow-Methods'] == 'PATCH,PUT'


async def test_wildcard_cors_methods(client, app):

    extensions.cors(app, methods='*')

    response = await client.get('/test')
    assert (response.headers['Access-Control-Allow-Methods'] ==
            ','.join(extensions.HTTP_METHODS))


async def test_custom_cors_headers(client, app):

    extensions.cors(app, headers=['X-Powered-By', 'X-Requested-With'])

    @app.route('/test')
    async def get(request, response):
        response.body = 'test response'

    response = await client.get('/test')
    assert (response.headers['Access-Control-Allow-Headers'] ==
            'X-Powered-By,X-Requested-With')


async def test_logger(client, app, capsys):

    # startup has yet been called, but logger extensions was not registered
    # yet, so let's simulate a new startup.
    app.hooks['startup'] = []
    extensions.logger(app)
    await app.startup()

    @app.route('/test')
    async def get(request, response):
        return 'test response'

    await client.get('/test')
    _, err = capsys.readouterr()
    assert err == 'GET /test\n'


async def test_json_with_default_code(client, app):

    @app.route('/test')
    async def get(request, response):
        response.json = {'key': 'value'}

    response = await client.get('/test')
    assert response.headers['Content-Type'] == 'application/json; charset=utf-8'
    assert json.loads(response.body.decode()) == {'key': 'value'}
    assert response.status == HTTPStatus.OK


async def test_json_with_custom_code(client, app):

    @app.route('/test')
    async def get(request, response):
        response.json = {'key': 'value'}
        response.status = 400

    response = await client.get('/test')
    assert response.headers['Content-Type'] == 'application/json; charset=utf-8'
    assert json.loads(response.body.decode()) == {'key': 'value'}
    assert response.status == HTTPStatus.BAD_REQUEST


async def test_traceback(client, app, capsys):

    extensions.traceback(app)

    @app.route('/test')
    async def get(request, response):
        raise ValueError('Unhandled exception')

    response = await client.get('/test')
    _, err = capsys.readouterr()
    assert response.status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert 'Unhandled exception' in err


async def test_options(client, app):

    extensions.options(app)

    @app.route('/test')
    async def get(request, response):
        raise  # Should not be called.

    response = await client.options('/test')
    assert response.status == HTTPStatus.OK


async def test_static(client, app):

    # startup has yet been called, but static extensions was not registered
    # yet, so let's simulate a new startup.
    app.hooks['startup'] = []
    extensions.static(app, root=Path(__file__).parent / 'static')
    await app.startup()

    response = await client.get('/static/index.html')
    assert response.status == HTTPStatus.OK
    assert b'Test' in response.body
    assert response.headers['Content-Type'] == 'text/html'

    response = await client.get('/static/style.css')
    assert response.status == HTTPStatus.OK
    assert b'chocolate' in response.body
    assert response.headers['Content-Type'] == 'text/css'


async def test_static_raises_if_path_is_outside_root(client, app):

    app.hooks['startup'] = []
    extensions.static(app, root=Path(__file__).parent / 'static')
    await app.startup()

    response = await client.get('/static/../../README.md')
    assert response.status == HTTPStatus.BAD_REQUEST


async def test_can_change_static_prefix(client, app):

    app.hooks['startup'] = []
    extensions.static(app, root=Path(__file__).parent / 'static',
                      prefix='/foo')
    await app.startup()

    response = await client.get('/foo/index.html')
    assert response.status == HTTPStatus.OK
    assert b'Test' in response.body


async def test_get_accept_content_negociation(client, app):

    extensions.content_negociation(app)

    @app.route('/test', accepts=['text/html'])
    async def get(request, response):
        response.headers['Content-Type'] = 'text/html'
        response.body = 'accepted'

    response = await client.get('/test', headers={'Accept': 'text/html'})
    assert response.status == HTTPStatus.OK
    assert response.body == b'accepted'
    assert response.headers['Content-Type'] == 'text/html'


async def test_get_accept_content_negociation_if_many(client, app):

    extensions.content_negociation(app)

    @app.route('/test', accepts=['text/html', 'application/json'])
    async def get(request, response):
        if request.headers['ACCEPT'] == 'text/html':
            response.headers['Content-Type'] = 'text/html'
            response.body = '<h1>accepted</h1>'
        elif request.headers['ACCEPT'] == 'application/json':
            response.json = {'status': 'accepted'}

    response = await client.get('/test', headers={'Accept': 'text/html'})
    assert response.status == HTTPStatus.OK
    assert response.body == b'<h1>accepted</h1>'
    assert response.headers['Content-Type'] == 'text/html'
    response = await client.get('/test', headers={'Accept': 'application/json'})
    assert response.status == HTTPStatus.OK
    assert json.loads(response.body.decode()) == {'status': 'accepted'}
    assert response.headers['Content-Type'] == 'application/json; charset=utf-8'


async def test_get_reject_content_negociation(client, app):

    extensions.content_negociation(app)

    @app.route('/test', accepts=['text/html'])
    async def get(request, response):
        response.body = 'rejected'

    response = await client.get('/test', headers={'Accept': 'text/css'})
    assert response.status == HTTPStatus.NOT_ACCEPTABLE


async def test_get_reject_content_negociation_if_no_accept_header(client, app):

    extensions.content_negociation(app)

    @app.route('/test', accepts=['*/*'])
    async def get(request, response):
        response.body = 'rejected'

    response = await client.get('/test')
    assert response.status == HTTPStatus.NOT_ACCEPTABLE


async def test_get_accept_star_content_negociation(client, app):

    extensions.content_negociation(app)

    @app.route('/test', accepts=['text/css'])
    async def get(request, response):
        response.body = 'accepted'

    response = await client.get('/test', headers={'Accept': 'text/*'})
    assert response.status == HTTPStatus.OK


async def test_post_accept_content_negociation(client, app):

    extensions.content_negociation(app)

    @app.route('/test', methods=['POST'], accepts=['application/json'])
    async def get(request, response):
        response.json = {'status': 'accepted'}

    client.content_type = 'application/x-www-form-urlencoded'
    response = await client.post('/test', body={'key': 'value'},
                             headers={'Accept': 'application/json'})
    assert response.status == HTTPStatus.OK
    assert response.headers['Content-Type'] == 'application/json; charset=utf-8'
    assert json.loads(response.body.decode()) == {'status': 'accepted'}


async def test_post_reject_content_negociation(client, app):

    extensions.content_negociation(app)

    @app.route('/test', methods=['POST'], accepts=['text/html'])
    async def get(request, response):
        response.json = {'status': 'accepted'}

    client.content_type = 'application/x-www-form-urlencoded'
    response = await client.post('/test', body={'key': 'value'},
                             headers={'Accept': 'application/json'})
    assert response.status == HTTPStatus.NOT_ACCEPTABLE
