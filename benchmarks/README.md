## Running locally

Create a venv, install requirements.txt dependencies, and then run:

    ./bench.sh
    ./bench.sh "roll sanic"  # To run only roll and sanic.


## Running remotely

You need Fabric v2 branch:

    pip install git+git://github.com/fabric/fabric@v2

then bootstrap the server:

    fab -eH user@ip.ip.ip.ip bootstrap

then run the benchmarks:

    fab -eH user@ip.ip.ip.ip bench
    fab -eH user@ip.ip.ip.ip bench --names "roll sanic"
