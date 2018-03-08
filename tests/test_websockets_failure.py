import pytest
import asyncio
import websockets


@pytest.mark.asyncio
async def test_websocket_failure(liveclient):

    @liveclient.app.route('/failure', websocket=True)
    async def failme(request, ws, **params):
        raise NotImplementedError('OUCH')

    # This should fail, it doesn't.
    websocket = await websockets.connect(liveclient.wsl + '/failure')
    await websocket.send('test')
    await websocket.close()
