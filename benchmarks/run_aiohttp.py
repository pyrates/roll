from aiohttp import web
import json


async def hello(request):
    name = request.match_info.get('name', '')
    return web.Response(body=json.dumps({'message': f'Hello {name}'}))


app = web.Application()
app.router.add_get('/hello/{name}', hello)

if __name__ == '__main__':
    web.run_app(app, port=8000)
