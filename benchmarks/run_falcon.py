import falcon

try:
    import ujson as json
except ImportError:
    import json as json


class HelloResource(object):
    def on_get(self, req, resp, parameter):
        resp.status = falcon.HTTP_200
        resp.body = json.dumps({'message': f'Hello {parameter}'})


app = falcon.API()
hello = HelloResource()
app.add_route('/hello/{parameter}', hello)
