function run_ab() {
  python run_$1.py &
  sleep 1
  PID=$!
  mkdir logs/
  time ab -c 50 -n 1000 http://127.0.0.1:8000/$2 > logs/$1-ab.log
  kill $PID
  wait $PID
  sleep 3
}

function run_wrk() {
  python run_$1.py &
  sleep 1
  PID=$!
  mkdir logs/
  time wrk -t10 -c50 -d15s http://127.0.0.1:8000/$2 > logs/$1-wrk.log
  kill $PID
  wait $PID
  sleep 3
}

# Run a first test to warm up Memory/CPU/HTTP connections,
# this way the order of tests below should not anymore be significant.
run_ab roll hello/bench

run_ab roll hello/bench
run_ab sanic hello/bench
run_ab aiohttp hello/bench

run_wrk roll hello/bench
run_wrk sanic hello/bench
run_wrk aiohttp hello/bench
