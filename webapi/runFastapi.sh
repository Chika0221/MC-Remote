#!/bin/sh
cd /home/chika/Projects/mc_beam/webapi
/usr/bin/gunicorn main:app -b 0.0.0.0:8000 --reload --workers 1 --threads 4 --log-level 'info' --worker-class 'uvicorn.workers.UvicornWorker'
