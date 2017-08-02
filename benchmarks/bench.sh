function run_ab() {
  python run_$1.py &
  sleep 1
  PID=$!
  mkdir logs/
  time ab -c 50 -n 1000 http://127.0.0.1:8000/$2 > logs/$1.log
  kill $PID
  wait $PID
  sleep 3
}

run_ab roll hello/bench  # White run to fill whatever is being filled(?!).

run_ab roll hello/bench
run_ab sanic hello/bench
run_ab aiohttp hello/bench
