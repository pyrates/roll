from sanic import Sanic
from sanic.response import json

app = Sanic(log_config=None)


@app.route('/hello/<parameter>')
async def hello(request, parameter):
    return json({'message': f'Hello {parameter}'})
