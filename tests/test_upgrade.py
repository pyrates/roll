from http import HTTPStatus

import pytest

from roll import HttpError, Protocol, ProtocolUpgrade, ProtocolStatus, Request
from roll.testing import Transport


pytestmark = pytest.mark.asyncio


class ReverseProcotol(ProtocolUpgrade):

    received = False
    
    def connection_lost(self, protocol, exc):
        raise NotImplementedError("We don't disconnect")

    def data_received(self, protocol, data):
        self.received = True
        raise NotImplementedError("We don't receive")

    def write(self, protocol, data):
        # We reverse the data$
        protocol.writer.write(bytes(list(reversed(data))))

    def __call__(self, protocol):
        return b'HTTP/1.1 101 Switching Protocols\r\n\r\n'


class ReverseAndEchoProcotol(ReverseProcotol):

    def write(self, protocol, data):
        # We reverse the data$
        protocol.writer.write(bytes(list(reversed(data))))
        protocol.writer.write(b'\n')
    write.bubble_up = True


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

SIMPLE_REQUEST = b'''
GET /test HTTP/1.1
Host: example.org
User-Agent: Lynx

'''


async def test_upgrade(protocol):
    protocol.data_received(UPGRADE_REQUEST)
    assert protocol.status == ProtocolStatus.UPGRADE_EXPECTED
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
    assert protocol.status == ProtocolStatus.NO_UPGRADE


async def test_setting_upgrade_wrong_type(protocol):
    upgrade = object()
    with pytest.raises(TypeError) as exc:
        protocol.upgrade_protocol(upgrade)
    assert str(exc.value) == (
        'Upgrade must be an instance of roll.ProtocolUpgrade')


async def test_setting_upgrade(protocol):
    upgrade = ReverseProcotol()
    protocol.upgrade_protocol(upgrade)
    protocol.status == ProtocolStatus.UPGRADED
    assert protocol.writer.data == b'HTTP/1.1 101 Switching Protocols\r\n\r\n'
    protocol.writer.data = b''  # We clean up the data for what's to come
    protocol.write(b'This is my test !')
    assert protocol.writer.data == b'! tset ym si sihT'


async def test_upgrade_notimplemented_bubbling(protocol):
    upgrade = ReverseProcotol()
    protocol.upgrade_protocol(upgrade)
    protocol.status == ProtocolStatus.UPGRADED
    assert protocol.upgrade.received == False
    protocol.data_received(SIMPLE_REQUEST)
    assert protocol.upgrade.received == True  # went through the upgrade
    assert protocol.request.url == b'/test'  # then processed normally


async def test_upgrade_explicit_bubbling(protocol):
    upgrade = ReverseAndEchoProcotol()
    protocol.upgrade_protocol(upgrade)
    protocol.status == ProtocolStatus.UPGRADED
    assert protocol.writer.data == b'HTTP/1.1 101 Switching Protocols\r\n\r\n'
    protocol.writer.data = b''  # We clean up the data for what's to come
    protocol.write(b'This is my test !')
    assert protocol.writer.data == b'! tset ym si sihT\nThis is my test !'
