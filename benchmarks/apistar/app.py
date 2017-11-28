import asyncio
import logging

import uvloop
from apistar import Route
# from apistar.frameworks.wsgi import WSGIApp as App
from apistar.frameworks.asyncio import ASyncIOApp as App

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
logging.getLogger('asyncio').setLevel(logging.CRITICAL)


async def minimal():
    return {'message': 'Hello, World!'}


routes = [
    Route('/hello/minimal', 'GET', minimal),
]

app = App(routes=routes)
