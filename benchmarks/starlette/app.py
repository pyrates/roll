from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route


async def minimal(request):
    return JSONResponse({'message': 'Hello, World!'})


app = Starlette(debug=False, routes=[
    Route('/hello/minimal', minimal),
])
