import uuid
from roll import Roll, Response
from roll.websockets import websockets
from roll.extensions import logger, simple_server, traceback


class HTMLResponse(Response):

    def html(self, body):
        self.headers['Content-Type'] = 'plain/text'
        self.body = body

        
class Application(Roll):
    Response = HTMLResponse


app = traceback(
    logger(
        websockets(
            Application())))


@app.route('/')
async def hello(request, response):
    response.html('Hello World !')


@app.websocket('/chat')
async def broadcast(request, ws, **params):
    wsid = str(uuid.uuid4())
    await ws.send('Welcome {} !'.format(wsid))
    async for message in ws:
        for (task, socket) in request.app['websockets']:
            if socket != ws:
                await socket.send('{}: {}'.format(wsid, message))
                

if __name__ == '__main__':
    import asyncio
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    simple_server(app)
