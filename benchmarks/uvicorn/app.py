import asyncio
import logging

import ujson as json

import uvloop

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
logging.getLogger('asyncio').setLevel(logging.CRITICAL)


async def app(message, channels):
    response = {
        'status': 200,
        'headers': [
            [b'content-type', b'application/json'],
        ],
        'content': json.dumps({'message': 'Hello, World!'}).encode()
    }
    await channels['reply'].send(response)
