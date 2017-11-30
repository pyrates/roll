#!/usr/bin/env bash

# exec gunicorn app:app --workers $WORKERS --threads $WORKERS --config gunicorn.conf
exec uvicorn app:app --workers $WORKERS --threads $WORKERS
