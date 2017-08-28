#!/usr/bin/env bash

export WORKERS=$WORKERS
exec python app.py

# exec gunicorn app:app --config gunicorn.conf
