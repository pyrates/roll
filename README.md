# Let’s roll.

# Philosophy

Make it small to make it big.

Roll is a pico framework with performances and aesthetic in mind.

## Install

    pip install roll


## Getting started

    from roll import Roll

    myapp = Roll()

    @myapp.route('/hello/:parameter')
    async def hello(request, response, parameter='world'):
        response.body = f'Hello {parameter}'


## Contains

* async everywhere
* basic routing through [kua](https://github.com/nitely/kua)
* extensible system through hooks, see extensions for inspiration
* decent HTTP errors


## Does NOT contain

* templating system
* stability (yet!)


## Run

    gunicorn path.to.your:app --bind 0.0.0.0:3579 --worker-class roll.worker.Worker --workers 4

You can try with `example:app` for instance.
