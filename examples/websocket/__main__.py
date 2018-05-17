import uuid
import uvloop
import asyncio
from pathlib import Path
from roll import Roll
from roll.extensions import static, simple_server


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


app = Roll()

# Exposing the html folder to serve the files
# Access : http://127.0.0.1:3579/static/websocket.html
htmlfiles = Path(__file__).parent.joinpath('html')
static(app, root=htmlfiles)


@app.route('/chat', protocol="websocket")
async def broadcast(request, ws, **params):
    wsid = str(uuid.uuid4())
    await ws.send(f'Welcome {wsid} !')
    async for message in ws:
        for socket in request.app.websockets:
            if socket != ws:
                await socket.send('{}: {}'.format(wsid, message))


if __name__ == '__main__':
    print('Example access : http://127.0.0.1:3579/static/websocket.html')
    simple_server(app)
