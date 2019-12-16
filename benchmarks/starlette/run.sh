#!/usr/bin/env bash

exec gunicorn app:app --workers $WORKERS --threads $WORKERS --config gunicorn.conf
