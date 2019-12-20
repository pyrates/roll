import pytest
import asyncio
import websockets
from http import HTTPStatus
from roll.extensions import websockets_store


@pytest.mark.asyncio
async def test_websocket_route(liveclient):
    ev = asyncio.Event()

    @liveclient.app.route('/ws', protocol="websocket")
    async def handler(request, ws, **params):
        assert ws.subprotocol is None
        ev.set()

    response = await liveclient.query('GET', '/ws', headers={
        'Upgrade': 'websocket',
        'Connection': 'upgrade',
        'Sec-WebSocket-Key': 'hojIvDoHedBucveephosh8==',
        'Sec-WebSocket-Version': '13'})

    assert ev.is_set()
    assert response.status == HTTPStatus.SWITCHING_PROTOCOLS

    # With keep-alive in Connection
    response = await liveclient.query('GET', '/ws', headers={
        'Upgrade': 'websocket',
        'Connection': 'keep-alive, upgrade',
        'Sec-WebSocket-Key': 'hojIvDoHedBucveephosh8==',
        'Sec-WebSocket-Version': '13'})

    assert response.status == HTTPStatus.SWITCHING_PROTOCOLS


@pytest.mark.asyncio
async def test_websocket_communication(liveclient):

    @liveclient.app.route('/echo', protocol="websocket")
    async def echo(request, ws, **params):
        while True:
            message = await ws.recv()
            await ws.send(message)

    # Echo
    websocket = await websockets.connect(liveclient.wsl + '/echo')
    try:
        for message in ('This', 'is', 'a', 'simple', 'test'):
            await websocket.send(message)
            echoed = await websocket.recv()
            assert echoed == message
    finally:
        await websocket.close()

    # Nothing sent, just close
    websocket = await websockets.connect(liveclient.wsl + '/echo')
    await websocket.close()


@pytest.mark.asyncio
async def test_websocket_broadcasting(app, liveclient):

    websockets_store(app)

    @app.route('/broadcast', protocol="websocket")
    async def feed(request, ws, **params):
        while True:
            message = await ws.recv()
            await asyncio.wait([
                socket.send(message) for socket
                in request.app['websockets'] if socket != ws])

    # connecting
    connected = []
    for n in range(1, 6):
        ws = await websockets.connect(liveclient.wsl + '/broadcast')
        connected.append(ws)

    # Broadcasting
    for wid, ws in enumerate(connected, 1):
        broadcast = 'this is a broadcast from {}'.format(wid)
        await ws.send(broadcast)
        for ows in connected:
            if ows != ws:
                message = await ows.recv()
                assert message == broadcast

    # Closing
    for ws in connected:
        await ws.close()


@pytest.mark.asyncio
async def test_websocket_binary(liveclient):

    @liveclient.app.route('/bin', protocol="websocket")
    async def binary(request, ws, **params):
        await ws.send(b'test')

    # Echo
    websocket = await websockets.connect(liveclient.wsl + '/bin')
    bdata = await websocket.recv()
    await websocket.close_connection_task
    assert bdata == b'test'
    assert websocket.close_reason == ''
    assert websocket.state == websockets.protocol.State.CLOSED


@pytest.mark.asyncio
async def test_websocket_route_with_subprotocols(liveclient):
    results = []

    @liveclient.app.route(
        '/ws', protocol="websocket", subprotocols=['foo', 'bar'])
    async def handler(request, ws):
        results.append(ws.subprotocol)

    response = await liveclient.query('GET', '/ws', headers={
        'Upgrade': 'websocket',
        'Connection': 'upgrade',
        'Sec-WebSocket-Key': 'dGhlIHNhbXBsZSBub25jZQ==',
        'Sec-WebSocket-Version': '13',
        'Sec-WebSocket-Protocol': 'bar'})
    assert response.status == HTTPStatus.SWITCHING_PROTOCOLS

    response = await liveclient.query('GET', '/ws', headers={
        'Upgrade': 'websocket',
        'Connection': 'upgrade',
        'Sec-WebSocket-Key': 'dGhlIHNhbXBsZSBub25jZQ==',
        'Sec-WebSocket-Version': '13',
        'Sec-WebSocket-Protocol': 'bar, foo'})
    assert response.status == HTTPStatus.SWITCHING_PROTOCOLS

    response = await liveclient.query('GET', '/ws', headers={
        'Upgrade': 'websocket',
        'Connection': 'upgrade',
        'Sec-WebSocket-Key': 'dGhlIHNhbXBsZSBub25jZQ==',
        'Sec-WebSocket-Version': '13',
        'Sec-WebSocket-Protocol': 'baz'})
    assert response.status == HTTPStatus.SWITCHING_PROTOCOLS

    response = await liveclient.query('GET', '/ws', headers={
        'Upgrade': 'websocket',
        'Connection': 'upgrade',
        'Sec-WebSocket-Key': 'dGhlIHNhbXBsZSBub25jZQ==',
        'Sec-WebSocket-Version': '13'})
    assert response.status == HTTPStatus.SWITCHING_PROTOCOLS
    assert results == ['bar', 'bar', None, None]
