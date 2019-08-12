# How-to guides: developing


## How to use a livereload development server

First, install [hupper](https://pypi.python.org/pypi/hupper).

Then turn your Roll service into an importable module. Basically, a folder with
`__init__.py` and `__main__.py` files and put your `simple_server` call within
the `__main__.py` file (see the `examples/basic` folder for… an example!).

Once you did that, you can run the server using `hupper -m examples.basic`.
Each and every time you modify a python file, the server will reload and
take into account your modifications accordingly.

One of the pros of using hupper is that you can even set an `ipdb` call within
your code and it will work seamlessly (as opposed to using solutions like
[entr](http://www.entrproject.org/)).


## How to test forms

In case of the login form from the
[dedicated tutorial](../tutorials#your-first-roll-form):

```python3
@app.route('/login', methods=['POST'])
async def login(request, response):
    username = request.form.get('username')
    password = request.form.get('password')
    response.body = f'Username: `{username}` password: `{password}`.'
```

Start to set the appropriated content type and then pass your data:

```python3
async def test_login_form(client):
    client.content_type = 'application/x-www-form-urlencoded'
    data = {'username': 'David', 'password': '123456'}
    resp = await client.post('/test', data=data)
    assert resp.status == HTTPStatus.OK
    assert resp.body == b'Username: `David` password: `123456`.'
```

Note that you can send files too, for instance with an upload avatar view:

```python3
@app.route('/upload/avatar', methods=['POST'])
async def upload_avatar(req, resp):
    filename = req.files.get('avatar').filename
    content = req.files.get('avatar').read()
    resp.body = f'{filename} {content}'
```

Start to set the appropriated content type and then pass your files content:

```python3
async def test_avatar_form(client, app):
    client.content_type = 'multipart/form-data'
    files = {'avatar': (b'foo', 'me.png')}
    resp = await client.post('/test', files=files)
    assert resp.status == HTTPStatus.OK
    assert resp.body == b'me.png foo'
```

## How to run Roll’s tests

Roll exposes a pytest fixture (`client`), and for this needs to be
properly installed so pytest sees it. Once in the roll root (and with
your virtualenv active), run:

    python setup.py develop

Then you can run the tests:

    py.test
