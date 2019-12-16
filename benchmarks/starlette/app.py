from starlette.applications import Starlette
from starlette.responses import UJSONResponse
from starlette.routing import Route


async def minimal(request):
    return UJSONResponse({'message': 'Hello, World!'})


app = Starlette(debug=False, routes=[
    Route('/hello/minimal', minimal),
])
