#!/usr/bin/env bash

gunicorn app:app --config gunicorn.conf &
