## Running locally

Create a venv, install requirements.txt dependencies, and then run:

    ./bench.sh
    ./bench.sh wrk  # To run only wrk suite
    ./bench.sh wrk "roll sanic"  # To run only roll and sanic with wrk.


## Running remotely

You need Fabric v2 branch:

    pip install git+git://github.com/fabric/fabric@v2

then bootstrap the server:

    fab -eH user@ip.ip.ip.ip bootstrap

then run the benchmarks:

    fab -eH user@ip.ip.ip.ip bench
    fab -eH user@ip.ip.ip.ip bench --tools ab --names "roll sanic"
