import pytest
import asyncio
from roll import Protocol
from roll.testing import Transport


@pytest.fixture
def protocol(app, event_loop):
    app.loop = event_loop
    protocol = Protocol(app)
    protocol.connection_made(Transport())
    return protocol


@pytest.mark.asyncio
async def test_not_persistent(protocol):
    protocol.data_received(
        b'GET /test HTTP/1.1\r\n'
        b'Host: localhost:1707\r\n'
        b'User-Agent: Lynx\r\n'
        b'Connection: Close\r\n'
        b'\r\n')
    assert protocol.keep_alive == False


@pytest.mark.asyncio
async def test_switch(protocol):

    # We keep the connection alive after the first request
    protocol.data_received(
        b'GET /test HTTP/1.1\r\n'
        b'Host: localhost:1707\r\n'
        b'User-Agent: Lynx\r\n'
        b'Connection: Keep-Alive\r\n'
        b'\r\n')
    assert protocol.keep_alive == True
    
    # We ask for close for the next request
    protocol.data_received(
        b'GET /test HTTP/1.1\r\n'
        b'Host: localhost:1707\r\n'
        b'User-Agent: Lynx\r\n'
        b'Connection: Close\r\n'
        b'\r\n')
    assert protocol.keep_alive == False

    # If we ask again, we are expected to be closed, so new keep_alive
    # Won't mean a thing, until we re-create a protocol.
    protocol.data_received(
        b'GET /test HTTP/1.1\r\n'
        b'Host: localhost:1707\r\n'
        b'User-Agent: Lynx\r\n'
        b'Connection: Keep-Alive\r\n'
        b'\r\n')
    assert protocol.keep_alive == False
