import pytest

from roll import plugins


@pytest.mark.asyncio
async def test_cors(req,  app):

    plugins.cors(app)

    @app.route('/test')
    async def get(req):
        return 'test response'

    resp = await req('/test')
    assert resp.status == b'200 OK'
    assert resp.body == 'test response'
    assert resp.headers['Allow-Cross-Origin'] == '*'


@pytest.mark.asyncio
async def test_custom_cors(req, app):

    plugins.cors(app, value='mydomain.org')

    @app.route('/test')
    async def get(req):
        return 'test response'

    resp = await req('/test')
    assert resp.headers['Allow-Cross-Origin'] == 'mydomain.org'


@pytest.mark.asyncio
async def test_logger(req, app, capsys):

    plugins.logger(app)

    @app.route('/test')
    async def get(req):
        return 'test response'

    await req('/test')
    _, err = capsys.readouterr()
    assert err == 'GET /test\n'
