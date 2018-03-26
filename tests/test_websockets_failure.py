# -*- coding: utf-8 -*-

import pytest
import asyncio
import websockets


@pytest.mark.asyncio
async def test_websocket_failure(liveclient):

    @liveclient.app.route('/failure', protocol="websocket")
    async def failme(request, ws, **params):
        raise NotImplementedError('OUCH')

    websocket = await websockets.connect(liveclient.wsl + '/failure')

    with pytest.raises(websockets.exceptions.ConnectionClosed) as exc:
        # The client has 5 second (set in the protocol) before the
        # closing handshake timeout and the brutal disconnection.
        # We wait beyond the closing frame timeout :
        await asyncio.sleep(6)

        # No, we try sending while the closing frame timespan has expired
        await websocket.send('first')

    # No need to close here, the closing was unilateral, as we
    # did not comply in time.
    # We check the remains of the disowned client :
    assert websocket.state == 3
    assert websocket.close_code == 1011
    assert websocket.close_reason == 'Handler died prematurely.'


@pytest.mark.asyncio
async def test_websocket_failure_intime(liveclient):

    @liveclient.app.route('/failure', protocol="websocket")
    async def failme(request, ws, **params):
        raise NotImplementedError('OUCH')

    websocket = await websockets.connect(liveclient.wsl + '/failure')
    # Sent within the closing frame span messages will be ignored but
    # won't create any error as the server is polite and awaits the
    # closing frame to ends the interaction in a friendly manner.
    await websocket.send('first')  

    # The server is on hold, waiting for the closing handshake
    # We provide it to be civilized.
    await websocket.close()
    
    # The websocket was closed with the error, but in a gentle way.
    # No exception raised.
    assert websocket.state == 3
    assert websocket.close_code == 1011
    assert websocket.close_reason == 'Handler died prematurely.'


@pytest.mark.asyncio
async def test_websocket_failure_receive(liveclient):

    @liveclient.app.route('/failure', protocol="websocket")
    async def failme(request, ws, **params):
        raise NotImplementedError('OUCH')

    websocket = await websockets.connect(liveclient.wsl + '/failure')
    with pytest.raises(websockets.exceptions.ConnectionClosed) as exc:
        # Receiving, on the other hand, will raise immediatly an
        # error as the reader is closed. Only the writer is opened
        # as we are expected to send back the closing frame.
        await websocket.recv()

    await websocket.close()
    assert websocket.state == 3  # closing state
    assert websocket.close_code == 1011
    assert websocket.close_reason == 'Handler died prematurely.'
