import pytest
import asyncio


@pytest.mark.asyncio
async def test_keep_alive(liveclient):

    @liveclient.app.route('/hello')
    async def hello(request, response):
        response.body = b'Hello !'

    @liveclient.app.route('/world')
    async def world(request, response):
        response.body = b'World !'

    @liveclient.app.route('/long')
    async def long_task(request, response):
        # The keep alive is in between requests, no during one.
        # So sleeping over the timeout time is of no consequence.
        await asyncio.sleep(11)
        response.body = b'I did a long task !'

    with liveclient as query:
        response = await query('GET', '/hello')
        assert response.status == 200
        assert response.read() == b'Hello !'

        response = await query('GET', '/world')
        assert response.status == 200
        assert response.read() == b'World !'

        response = await query('GET', '/unknown')
        assert response.status == 404
        assert response.read() == b'/unknown'

        response = await query('GET', '/long')
        assert response.status == 200
        assert response.read() == b'I did a long task !'
        
        response = await query('GET', '/world')
        assert response.status == 200
        assert response.read() == b'World !'
        
        await asyncio.sleep(11)  # Currently the timeout is set to 10

        response = await query('GET', '/hello')
        assert response.status == 408  # Request Timeout
