import pytest

from roll import extensions


@pytest.mark.asyncio
async def test_cors(req,  app):

    extensions.cors(app)

    @app.route('/test')
    async def get(req):
        return 'test response'

    resp = await req('/test')
    assert resp.status == b'200 OK'
    assert resp.body == 'test response'
    assert resp.headers['Allow-Cross-Origin'] == '*'


@pytest.mark.asyncio
async def test_custom_cors(req, app):

    extensions.cors(app, value='mydomain.org')

    @app.route('/test')
    async def get(req):
        return 'test response'

    resp = await req('/test')
    assert resp.headers['Allow-Cross-Origin'] == 'mydomain.org'


@pytest.mark.asyncio
async def test_logger(req, app, capsys):

    extensions.logger(app)

    @app.route('/test')
    async def get(req):
        return 'test response'

    await req('/test')
    _, err = capsys.readouterr()
    assert err == 'GET /test\n'
