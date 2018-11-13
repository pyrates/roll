import asyncio

import responder
import uvloop

api = responder.API()

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


@api.route('/hello/minimal')
async def minimal(request, response):
    response.media = {'message': 'Hello, World!'}


if __name__ == '__main__':
    api.run(port=8000, access_log=False)
