from roll import Roll
from roll.plugins import cors

app = Roll()
cors(app)


@app.route('/')
async def home(req):
    return 'Hello World', 200


@app.listen('startup')
async def on_startup():
    print("Let's Roll!")


@app.listen('request')
async def log_request(request):
    print("Served request…", request.method, request.path)


if __name__ == '__main__':
    app.serve()
