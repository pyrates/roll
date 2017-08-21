from aiohttp import web

try:
    import ujson as json
except ImportError:
    import json as json


async def hello(request):
    parameter = request.match_info.get('parameter', '')
    return web.Response(body=json.dumps({'message': f'Hello {parameter}'}))


app = web.Application()
app.router.add_get('/hello/{parameter}', hello)
