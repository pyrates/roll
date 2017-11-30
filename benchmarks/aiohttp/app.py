from aiohttp import web


async def minimal(request):
    return web.json_response({'message': 'Hello, World!'})


async def parameter(request):
    parameter = request.match_info.get('parameter', '')
    return web.json_response({'message': parameter})


app = web.Application()
app.router.add_get('/hello/minimal', minimal)
app.router.add_get('/hello/with/{parameter}', parameter)
