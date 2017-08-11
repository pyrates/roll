#!/usr/bin/env bash

mkdir -p logs/

function run_ab() {
  ab -c 50 -n 1000 http://127.0.0.1:8000/$URLPATH
}

function run_wrk() {
  wrk -t20 -c100 -d20s http://127.0.0.1:8000/$URLPATH
}

function run () {
  echo "Running bench with $TOOL for $NAME"
  cd $NAME && . ./run.sh &
  sleep 1
  PID=$!
  http "http://127.0.0.1:8000/$URLPATH"
  time run_$TOOL | tee $NAME/$TOOL.log
  kill $PID
  wait $PID
}

if test -z "$2"
then
  TOOLS="ab wrk"
else
  TOOLS=$1
fi

if test -z "$2"
then
  NAMES="aiohttp falcon roll sanic"
else
  NAMES=$2
fi
LEN=${#NAMES[@]}


URLPATH=hello/bench
for TOOL in $TOOLS
do
  COUNTER=0
  for NAME in $NAMES
  do
    echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
    run $TOOL $NAME hello/bench
    let COUNTER++
    if (($COUNTER < $LEN))
      then sleep 20
    fi
    echo "<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<"
  done
done
