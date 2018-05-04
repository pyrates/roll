# How-to guides

A how-to guide:

* is goal-oriented
* shows how to solve a specific problem
* is a series of steps

*Analogy: a recipe in a cookery book*


## How to install Roll

Roll requires Python 3.5+ to be installed.

It is recommended to install it within
[a pipenv or virtualenv](http://docs.python-guide.org/en/latest/dev/virtualenvs/).

You can install Roll through [pip](https://pip.pypa.io/en/stable/):

    pip install roll


## How to return an HTTP error

There are many reasons to return an HTTP error, with Roll you have to
raise an HttpError instance. Remember our
[base example from tutorial](/tutorials.md#your-first-roll-application)?
What if we want to return an error to the user:

```python3
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
[base example from tutorial](/tutorials.md#your-first-roll-application)?

```python3
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
Content-Type: application/json; charset=utf-8

{
    "hello": "world"
}
```

Especially useful for APIs.


## How to serve HTML templates

There is an example in the `examples/html` folder using
[Jinja2](http://jinja.pocoo.org/) to render and return HTML views.

To run it, go to the `examples` folder and run `python -m html`.
Now reach `http://127.0.0.1:3579/hello/world` with your browser.

To run associated tests: `py.test html/tests.py`.


## How to store custom data in the request

You can use `Request` as a `dict` like object for your own use, `Roll` itself
never touches it.

```python3
request['user'] = get_current_user()
```


## How to deal with cookies

### Request cookies

If the request has any `Cookie` header, you can retrieve it with the
`request.cookies` attribute, using the cookie `name` as key:

```python3
value = request.cookies['name']
```


### Response cookies

You can add cookies to response using the `response.cookies` attribute:

```python3
response.cookies.set(name='name', value='value', path='/foo')
```

See the [reference](/reference.md#cookies) for all the available `set` kwargs.


See also the [advanced guides](/how-to/advanced.md).
