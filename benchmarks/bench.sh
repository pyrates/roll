#!/usr/bin/env bash

while [[ "$#" > 1 ]]; do case $1 in
    --frameworks) FRAMEWORKS="$2";;
    --endpoint) ENDPOINT="$2";;
    --workers) WORKERS="$2";;
    *) break;;
  esac; shift; shift
done

WORKERS=${WORKERS:-1}
ENDPOINT=${ENDPOINT:-minimal}
FRAMEWORKS=${FRAMEWORKS:-sanic roll}


function run_minimal() {
  URL="http://127.0.0.1:8000/hello/minimal"
  http $URL
  time wrk -t1 -c100 -d10s $URL | tee $NAME/wrk.log
}

function run_parameter() {
  URL="http://127.0.0.1:8000/hello/with/foobar"
  http $URL
  time wrk -t1 -c100 -d10s $URL | tee $NAME/wrk.log
}

function run_cookie() {
  URL="http://127.0.0.1:8000/hello/cookie"
  http $URL Cookie:"test=bench"
  time wrk -t1 -c100 -d10s -H "Cookie: test=bench" $URL | tee $NAME/wrk.log
}

function run_query() {
  URL="http://127.0.0.1:8000/hello/query?query=foobar"
  http $URL
  time wrk -t1 -c100 -d10s $URL | tee $NAME/wrk.log
}

function run_full() {
  URL="http://127.0.0.1:8000/hello/full/with/foo/and/bar?query=foobar"
  http $URL Cookie:"test=bench"
  time wrk -t1 -c100 -d10s -H "Cookie: test=bench" $URL | tee $NAME/wrk.log
}


function run () {
  echo "Running bench for $NAME on $ENDPOINT endpoint with $WORKERS worker(s)"
  cd $NAME && . ./run.sh &
  sleep 1
  PID=$!
  run_$ENDPOINT
  kill $PID
  wait $PID
}

LEN=${#NAMES[@]}
COUNTER=0
for NAME in $FRAMEWORKS
do
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  run
  let COUNTER++
  if (($COUNTER < $LEN))
    then sleep 20
  fi
  echo "<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<"
done
