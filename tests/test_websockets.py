# -*- coding: utf-8 -*-

import pytest
import asyncio


@pytest.mark.asyncio
async def test_websocket_route(wsclient, wsapp):
    ev = asyncio.Event()

    @wsapp.route('/ws', websocket=True)
    async def handler(request, ws, **params):
        assert ws.subprotocol is None
        ev.set()

    response = await wsclient.get('/ws', headers={
        'Upgrade': 'websocket',
        'Connection': 'upgrade',
        'Sec-WebSocket-Key': 'dGhlIHNhbXBsZSBub25jZQ==',
        'Sec-WebSocket-Version': '13'})
    assert ev.is_set()


    @wsapp.route('/ws', websocket=True, methods=['POST'])
    async def handler(request, ws, **params):
        assert ws.subprotocol is None
        ev.set()
