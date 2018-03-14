from http import HTTPStatus

import pytest

from roll import HttpError, Protocol, Request
from roll import HTTP_FLOW, HTTP_NEEDS_UPGRADE, HTTP_UPGRADED
from roll.testing import Transport


pytestmark = pytest.mark.asyncio


@pytest.fixture
def protocol(app, event_loop):
    app.loop = event_loop
    protocol = Protocol(app)
    protocol.connection_made(Transport())
    return protocol



UPGRADE_REQUEST = b'''
GET / HTTP/1.1
Host: example.org
Connection: Upgrade, HTTP2-Settings
Upgrade: h2c
HTTP2-Settings: <some settings>
User-Agent: Lynx

'''

UNCOMPLETE_UPGRADE_REQUEST = b'''
GET / HTTP/1.1
Host: example.org
Connection: Upgrade
User-Agent: Lynx

'''

async def test_upgrade(protocol):

    protocol.data_received(UPGRADE_REQUEST)

    assert protocol.status == HTTP_NEEDS_UPGRADE
    assert protocol.upgrade == None
    assert protocol.upgrade_type == 'h2c'
    protocol.write(
        "We shouldn't be answering without acknowledging the upgrade.")
    assert protocol.writer.data == (
        b'HTTP/1.1 501 Not Implemented\r\n'
        b'Content-Length: 40\r\n'
        b'\r\n'
        b'Expected upgrade to h2c protocol failed.'
    )

async def test_malformed_upgrade(protocol):

    protocol.data_received(UNCOMPLETE_UPGRADE_REQUEST)
    assert protocol.status == HTTP_FLOW
