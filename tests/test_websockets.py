# -*- coding: utf-8 -*-

import pytest
import asyncio
import websockets


@pytest.mark.asyncio
async def test_websocket_route(liveclient):
    ev = asyncio.Event()

    @liveclient.app.route('/ws', websocket=True)
    async def handler(request, ws, **params):
        assert ws.subprotocol is None
        ev.set()

    body, response = await liveclient.query('get', '/ws', headers={
        'Upgrade': 'websocket',
        'Connection': 'upgrade',
        'Sec-WebSocket-Key': 'hojIvDoHedBucveephosh8==',
        'Sec-WebSocket-Version': '13'})
    assert ev.is_set()
    assert response.status == 101

    with pytest.raises(RuntimeError) as exc:
        @liveclient.app.route('/ws', websocket=True, methods=['POST'])
        async def handler(request, ws, **params):
            assert ws.subprotocol is None
            ev.set()

    assert str(exc.value) == 'Websockets can only handshake on GET'


@pytest.mark.asyncio
async def test_websocket_communication(liveclient):

    @liveclient.app.route('/echo', websocket=True)
    async def echo(request, ws, **params):
        async for message in ws:
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
async def test_websocket_broadcasting(liveclient):

    @liveclient.app.route('/broadcast', websocket=True)
    async def feed(request, ws, **params):
        async for message in ws:
            for (task, socket) in request.app.websockets:
                if socket != ws:
                    await socket.send(message)

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
