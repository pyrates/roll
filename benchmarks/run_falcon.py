import falcon
import json
from wsgiref import simple_server


class HelloResource(object):
    def on_get(self, req, resp, param):
        resp.status = falcon.HTTP_200
        resp.body = json.dumps({'message': f'Hello {param}'})


app = falcon.API()
hello = HelloResource()
app.add_route('/hello/{param}', hello)

if __name__ == '__main__':
    httpd = simple_server.make_server('127.0.0.1', 8000, app)
    httpd.serve_forever()
