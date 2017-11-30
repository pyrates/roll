## Running locally

Create a venv, install requirements.txt dependencies, and then run:

    ./bench.sh
    ./bench.sh --frameworks "roll sanic"  # To run only roll and sanic.
    ./bench.sh --frameworks "roll sanic" --endpoint full  # To run only roll and
                                                          # sanic with "full" endpoint.
    ./bench.sh --frameworks "roll sanic" --workers 2  # To run only roll and sanic
                                                      # with 2 processes.


## Running remotely

You need Fabric v2 branch:

    pip install git+git://github.com/fabric/fabric@v2

then bootstrap the server:

    fab -eH user@ip.ip.ip.ip bootstrap

then run the benchmarks:

    fab -eH user@ip.ip.ip.ip bench
    fab -eH user@ip.ip.ip.ip bench --tools ab --names "roll sanic"
