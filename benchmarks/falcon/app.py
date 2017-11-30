import falcon

try:
    import ujson as json
except ImportError:
    import json as json


class MinimalResource:
    def on_get(self, req, resp):
        resp.status = falcon.HTTP_200
        resp.body = json.dumps({'message': 'Hello, World!'})


class ParameterResource:
    def on_get(self, req, resp, parameter):
        resp.status = falcon.HTTP_200
        resp.body = json.dumps({'parameter': parameter})


app = falcon.API()
app.add_route('/hello/minimal', MinimalResource())
app.add_route('/hello/with/{parameter}', ParameterResource())
