#!/usr/bin/env bash

exec hypercorn app:app --workers $WORKERS
