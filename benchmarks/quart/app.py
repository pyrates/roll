from quart import jsonify, Quart

app = Quart(__name__)


@app.route('/hello/minimal')
async def minimal():
    return jsonify({'message': 'Hello, World!'})
