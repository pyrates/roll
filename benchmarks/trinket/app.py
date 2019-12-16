from trinket import Trinket, Response


app = Trinket()


@app.route('/hello/minimal')
async def minimal(request):
    response = Response.json({'message': 'Hello, World!'})
    return response


@app.route('/hello/with/{parameter}')
async def parameter(request, parameter):
    response.json = Response.json({'parameter': parameter})


@app.route('/hello/cookie')
async def cookie(request):
    response = Response.json({'cookie': request.cookies['test']})
    response.cookies.set(name='bench', value='value')
    return response


@app.route('/hello/query')
async def query(request):
    response = Response.json({'query': request.query.get('query')})
    return response


@app.route('/hello/full/with/{one}/and/{two}')
async def full(request, one, two):
    response = Response.json({
        'parameters': f'{one} and {two}',
        'query': request.query.get('query'),
        'cookie': request.cookies['test'],
    })
    response.cookies.set(name='bench', value='value')
    return response


if __name__ == '__main__':
    app.start(host='127.0.0.1', port=8000, debug=False)
