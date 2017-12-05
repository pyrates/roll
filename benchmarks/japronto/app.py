from japronto import Application


async def minimal(request):
    return request.Response(json={'message': 'Hello, World!'})


async def parameter(request):
    return request.Response(
        json={'parameter': request.match_dict['parameter']})


app = Application()

r = app.router
r.add_route('/hello/minimal', minimal, method='GET')
r.add_route('/hello/with/{parameter}', parameter, method='GET')


if __name__ == '__main__':
    app.run(port=8000)
