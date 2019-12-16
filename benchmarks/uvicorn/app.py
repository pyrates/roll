import asyncio
import logging

import ujson as json
import uvloop

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
logging.getLogger('asyncio').setLevel(logging.CRITICAL)


async def app(scope, receive, send):
    assert scope['type'] == 'http'
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [
            [b'content-type', b'application/json'],
        ]
    })
    await send({
        'type': 'http.response.body',
        'body': json.dumps({'message': 'Hello, World!'}).encode(),
    })
