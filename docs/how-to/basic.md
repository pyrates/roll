# How-to guides

A how-to guide:

* is goal-oriented
* shows how to solve a specific problem
* is a series of steps

*Analogy: a recipe in a cookery book*


## How to install Roll

Roll requires Python 3.6+ to be installed.

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

See the [reference](/reference/core/#cookies) for all the available `set` kwargs.


## How to consume query parameters

The query parameters (a.k.a. URL parameters) are made accessible via the `request.query`
property.

The very basic usage is:

```python3
# URL looks like http://localhost/path?myparam=blah
myparam = request.query.get('myparam', 'default-value')
assert myparam == 'blah'
other = request.query.get('other', 'default-value')
assert other == 'default-value'
```

You can also request the full list of values:

```python3
# URL looks like http://localhost/path?myparam=bar&myparam=foo
myparam = request.query.list('myparam', 'default-value')
assert myparam == ['bar', 'foo']
```

If you don't pass a default value, Roll will assume that you are getting a required
parameter, and so if this parameter is not present in the query,
a `400` [HttpError](/reference/core/#httperror) will be raised.

The [Query](/reference/core/#query) class has three getters to cast the value for
you: `bool`, `int` and `float`.

```python3
# URL looks like http://localhost/path?myparam=true
myparam = request.query.bool('myparam', False)
assert myparam is True
```

If the parameter value cannot be casted, a `400` [HttpError](/reference/core/#httperror)
will be raised.

See also "[how to subclass roll itself](/how-to/advanced.md#how-to-subclass-roll-itself)"
to see how to make your own Query getters.


## How to use class-based views

In many situations, a `function` is sufficient to handle a request, but in some
cases, using classes helps reducing code boilerplate and keeping things DRY.

Using class-based views with Roll is straightforward:


```python3
@app.route('/my/path/{myvar}')
class MyView:

    def on_get(self, request, response, myvar):
        do_something_on_get

    def on_post(self, request, response, myvar):
        do_something_on_post
```

As you may guess, you need to provide an `on_xxx` method for each HTTP method
your view needs to support.

Of course, class-based views can inherit and have inheritance:

```python3
class View:
    CUSTOM = None

    async def on_get(self, request, response):
        response.body = self.CUSTOM

@app.route("/tomatoes")
class Tomato(View):
    CUSTOM = "tomato"

@app.route("/cucumbers")
class Cucumber(View):
    CUSTOM = "cucumber"

@app.route("/gherkins")
class Gherkin(Cucumber):
    CUSTOM = "gherkin"
```

Warning: Roll will instanciate the class once per thread (to avoid overhead at each
request), so their state will be shared between requests, thus make sure not to
set instance properties on them.


See also the [advanced guides](/how-to/advanced.md).
