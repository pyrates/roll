#!/usr/bin/env bash

mkdir -p logs/

function run_ab() {
  cd $1 && source ./run.sh && cd ..
  sleep 1
  PID=$!
  http "http://127.0.0.1:8000/$2"
  time ab -c 50 -n 1000 http://127.0.0.1:8000/$2 >> $1/ab.log
  kill $PID
  wait $PID
}

function run_wrk() {
  cd $1; source ./run.sh; cd ..
  sleep 1
  PID=$!
  http "http://127.0.0.1:8000/$2"
  time wrk -t20 -c100 -d20s http://127.0.0.1:8000/$2 >> $1/wrk.log
  kill $PID
  wait $PID
  tail -2 $1/wrk.log
}

if test -z "$1"
then
  NAMES="aiohttp falcon roll sanic"
else
  NAMES=$1
fi
LEN=${#NAMES[@]}

# COUNTER=0
# for NAME in $NAMES
# do
#   echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
#   echo "Running bench with ab for $NAME"
#   run_ab $NAME hello/bench
#   let COUNTER++
#   if (($COUNTER < $LEN))
#     then sleep 20
#   fi
#   echo "<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<"
# done

COUNTER=0
for NAME in $NAMES
do
  echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
  echo "Running bench with wrk for $NAME"
  run_wrk $NAME hello/bench
  let COUNTER++
  echo "<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<"
  if (($COUNTER < $LEN))
    then sleep 20
  fi
done
