from http import HTTPStatus

import pytest

from roll import HttpError, Protocol, Request
from roll import HTTP_FLOW, HTTP_NEEDS_UPGRADE, HTTP_UPGRADED
from roll.testing import Transport


pytestmark = pytest.mark.asyncio


@pytest.fixture
def protocol(app):
    protocol = Protocol(app)
    protocol.connection_made(Transport())
    return protocol


async def test_upgrade(protocol):

    protocol.data_received(
        b'POST /post HTTP/1.1\r\n'
        b'Upgrade: h2\r\n'
        b'Connection: Upgrade, HTTP2-Settings\r\n'
        b'HTTP2-Settings: My HTTP2 settings in b64\r\n'
        b'\r\n'
    )
    assert protocol.status == HTTP_NEEDS_UPGRADE
    assert protocol.upgrade == None
    assert protocol.upgrade_type.type == 'h2'
    assert protocol.upgrade_type.headers == {'UPGRADE', 'HTTP2-SETTINGS'}
    await protocol.task
    assert protocol.writer.data == (
        b'HTTP/1.1 501 Not Implemented\r\n'
        b'Content-Length: 39\r\n'
        b'\r\n'
        b'Expected upgrade to h2 protocol failed.'
    )

async def test_malformed_upgrade(protocol):

    protocol.data_received(
        b'POST /post HTTP/1.1\r\n'
        b'Upgrade: h2\r\n'
        b'Connection: Upgrade, HTTP2-Settings\r\n'
        b'\r\n'
    )
    assert protocol.writer.data == (
        b'HTTP/1.1 400 Bad Request\r\n'
        b'Content-Length: 18\r\n'
        b'\r\n'
        b'Unparsable request'
    )
