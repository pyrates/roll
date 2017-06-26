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
    # Because https://www.youtube.com/watch?v=hh9rUe_JARE
    print("Ready to roll out!")


if __name__ == '__main__':
    app.serve()
