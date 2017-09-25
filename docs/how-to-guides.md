# How-to guides

A how-to guide:

* is goal-oriented
* shows how to solve a specific problem
* is a series of steps

*Analogy: a recipe in a cookery book*


## How to install Roll

You can install Roll through [pip](https://pip.pypa.io/en/stable/):

    pip install roll

It is recommended to install it within
[a pipenv or virtualenv](http://docs.python-guide.org/en/latest/dev/virtualenvs/) though.


## How to create an extension

You can use extensions to achieve a lot of enhancements of the base
framework.

Basically, an extension is a function listening to
[events](reference.md#events), for instance:

```python
def cors(app, value='*'):

    @app.listen('response')
    async def add_cors_headers(response, request):
        response.headers['Access-Control-Allow-Origin'] = value
```

Here the `cors` extension can be applied to the Roll `app` object.
It listens to the `response` event and for each of those add a custom
header. The name of the inner function is not relevant but explicit is
always a bonus. The `response` object is modified in place.

*Note: more [extensions](reference.md#events) are available by default.
Make sure to check these out!*


## How to return an HTTP error

There are many reasons to return an HTTP error, with Roll you have to
raise an HttpError instance. Remember our
[base example from tutorial](tutorials.md#your-first-roll-application)?
What if we want to return an error to the user:

```python
from http import HTTPStatus

from roll import Roll, HttpError
from roll.extensions import simple_server

app = Roll()


@app.route('/hello/{parameter}')
async def hello(request, response, parameter):
    if parameter == 'foo':
        raise HttpError(HTTPStatus.BAD_REQUEST, 'Run, you foo(l)!')
    response.body = f'Hello {parameter}'


if __name__ == '__main__':
    simple_server(app)
```

Now when we try to reach the view with the `foo` parameter:

```
$ http :3579/hello/foo
HTTP/1.1 400 Bad Request
Content-Length: 16

Run, you foo(l)!
```

One advantage of using the exception mechanism is that you can raise an
HttpError from anywhere and let Roll handle it!


## How to return JSON content

There is a shortcut to return JSON content from a view. Remember our
[base example from tutorial](tutorials.md#your-first-roll-application)?

```python
from roll import Roll
from roll.extensions import simple_server

app = Roll()


@app.route('/hello/{parameter}')
async def hello(request, response, parameter):
    response.json = {'hello': parameter}


if __name__ == '__main__':
    simple_server(app)
```

Setting a `dict` to `response.json` will automagically dump it to
regular JSON and set the appropriated content type:

```
$ http :3579/hello/world
HTTP/1.1 200 OK
Content-Length: 17
Content-Type: application/json

{
    "hello": "world"
}
```

Especially useful for APIs.


## How to subclass Roll itself

Let’s say you want your own [Query](reference.md#core-objects) parser
to deal with GET parameters that should be converted as `datetime.date`
objects.

What you can do is subclass both the Roll class and the Protocol one
to set your custom Query class:

```python
from datetime import date

from roll import Roll, Query
from roll.extensions import simple_server


class MyQuery(Query):

    @property
    def date(self):
        return date(int(self.get('year')),
                    int(self.get('month')),
                    int(self.get('day')))


class MyProtocol(Roll.Protocol):
    Query = MyQuery


class MyRoll(Roll):
    Protocol = MyProtocol


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


## How to run Roll’s tests

Roll exposes a pytest fixture (`client`), and for this needs to be
properly installed so pytest sees it. Once in the roll root (and with
your virtualenv active), run:

    python setup.py develop

Then you can run the tests:

    py.test
