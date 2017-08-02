from sanic import Sanic
from sanic.response import json

app = Sanic()


@app.route('/hello/<param>')
async def hello(request, param):
    return json({'message': f'Hello {param}'})

if __name__ == '__main__':
    # disable internal messages
    app.run(debug=False, log_config=None, port=8000)
