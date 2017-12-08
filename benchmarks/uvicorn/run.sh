#!/usr/bin/env bash

exec uvicorn app:app --workers $WORKERS --threads $WORKERS
