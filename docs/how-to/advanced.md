# How-to guides: advanced


## How to create an extension

You can use extensions to achieve a lot of enhancements of the base
framework.

Basically, an extension is a function listening to
[events](/reference.md#events), for instance:

```python3
def cors(app, value='*'):

    @app.listen('response')
    async def add_cors_headers(response, request):
        response.headers['Access-Control-Allow-Origin'] = value
```

Here the `cors` extension can be applied to the Roll `app` object.
It listens to the `response` event and for each of those add a custom
header. The name of the inner function is not relevant but explicit is
always a bonus. The `response` object is modified in place.

*Note: more [extensions](/reference.md#events) are available by default.
Make sure to check these out!*


## How to deal with content negociation

The [`content_negociation` extension](/reference.md#content_negociation)
is made for this purpose, you can use it that way:

```python3
extensions.content_negociation(app)

@app.route('/test', accepts=['text/html', 'application/json'])
async def get(req, resp):
    if req.headers['ACCEPT'] == 'text/html':
        resp.headers['Content-Type'] = 'text/html'
        resp.body = '<h1>accepted</h1>'
    elif req.headers['ACCEPT'] == 'application/json':
        resp.json = {'status': 'accepted'}
```

Requests with `Accept` header not matching `text/html` or
`application/json` will be honored with a `406 Not Acceptable` response.


## How to subclass Roll itself

Let’s say you want your own [Query](/reference.md#query) parser
to deal with GET parameters that should be converted as `datetime.date`
objects.

What you can do is subclass the [Roll](/reference.md#roll) class
to set your custom Query class:

```python3
from datetime import date

from roll import Roll, Query
from roll.extensions import simple_server


class MyQuery(Query):

    @property
    def date(self):
        return date(int(self.get('year')),
                    int(self.get('month')),
                    int(self.get('day')))


class MyRoll(Roll):
    Query = MyQuery


app = MyRoll()


@app.route('/hello/')
async def hello(request, response):
    response.body = request.query.date.isoformat()


if __name__ == '__main__':
    simple_server(app)
```

And now when you pass appropriated parameters (for the sake of brievety,
no error handling is performed but hopefully you get the point!):

```
$ http :3579/hello/ year==2017 month==9 day==20
HTTP/1.1 200 OK
Content-Length: 10

2017-09-20
```


## How to deploy Roll into production

The recommended way to deploy Roll is using
[Gunicorn](http://docs.gunicorn.org/).

First install gunicorn in your virtualenv:

    pip install gunicorn

To run it, you need to pass it the pythonpath to your roll project
application. For example, if you have created a module `core.py`
in your package `mypackage`, where you create your application
with `app = Roll()`, then you need to issue this command line:

    gunicorn mypackage.core:app --worker roll.worker.Worker

See [gunicorn documentation](http://docs.gunicorn.org/en/stable/settings.html)
for more details about the available arguments.

Note: it's also recommended to install [uvloop](https://github.com/MagicStack/uvloop)
as a faster `asyncio` event loop replacement:

    pip install uvloop

## How to send custom events

Roll has a very small API for listening and sending events. It's possible to use
it in your project for your own events.

Events are useful when you want other users to extend your own code, whether
it's a Roll extension, or a full project built with Roll.
They differ from configuration in that they are more adapted for dynamic
modularity.

For example, say we develop a DB pooling extension for Roll. We
would use a simple configuration parameter to let users change the connection
credentials (host, username, password…). But if we want users to run some
code each time a new connection is created, we may use a custom event.

Our extension usage would look like this:

```python3
app = Roll()
db_pool_extension(app, dbname='mydb', username='foo', password='bar')

@app.listen('new_connection')
def listener(connection):
    # dosomething with the connection,
    # for example register some PostgreSQL custom types.
```

Then, in our extension, when creating a new connection, we'd do something like
that:

```python3
app.hook('new_connection', connection=connection)
```


## How to protect a view with a decorator

Here is a small example of a `WWW-Authenticate` protection using a decorator. Of
course, the decorator pattern can be used to any kind of more advanced
authentication process.


```python3
from base64 import b64decode

from roll import Roll


def auth_required(func):

    async def wrapper(request, response, *args, **kwargs):
        auth = request.headers.get('AUTHORIZATION', '')
        # This is really naive, never do that at home!
        if b64decode(auth[6:]) != b'user:pwd':
            response.status = HTTPStatus.UNAUTHORIZED
            response.headers['WWW-Authenticate'] = 'Basic'
        else:
            await func(request, response, *args, **kwargs)

    return wrapper


app = Roll()


@app.route('/hello/')
@auth_required
async def hello(request, response):
    pass
```


## How to work with Websockets pings and pongs

While most clients will keep the connection alive and won't expect
heartbeats (read ping), some can be more pedantic and ask for a regular
keep-alive ping.

```python
import asyncio

async def keep_me_alive(request, ws, **params):
    while True:
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=20)
        except asyncio.TimeoutError:
            # No data in 20 seconds, check the connection.
            try:
                pong_waiter = await ws.ping()
                await asyncio.wait_for(pong_waiter, timeout=10)
            except asyncio.TimeoutError:
                # No response to ping in 10 seconds, disconnect.
                break
        else:
            # do something with msg
            ...
```
