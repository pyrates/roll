#!/usr/bin/env bash

exec gunicorn app:app --config gunicorn.conf
