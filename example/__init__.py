from roll import Roll
from roll.extensions import cors, logger

app = Roll()
cors(app)
logger(app)


@app.route('/')
async def home(req):
    return 'Hello World', 200


@app.listen('startup')
async def on_startup():
    print("Let's Roll!")


if __name__ == '__main__':
    app.serve()
