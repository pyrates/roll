import pytest

from . import Request


@pytest.fixture
def req(app):

    async def _(path, method='GET'):
        req = Request()
        req.path = path
        req.method = method
        return await app.respond(req)

    return _
