# -*- coding: utf-8 -*-

import pytest
import asyncio


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
