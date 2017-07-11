import pytest

from . import Request


@pytest.yield_fixture
def req(app, event_loop):
    app.loop = event_loop
    app.loop.run_until_complete(app.startup())

    async def _(path, method='GET'):
        req = Request()
        req.on_url(path.encode())
        req.method = method
        return await app.respond(req)

    yield _

    app.loop.run_until_complete(app.shutdown())
