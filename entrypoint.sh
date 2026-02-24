#!/bin/bash

# Run Gunicorn with the specified arguments
# --access-logfile - logs to stdout, --log-file - logs to stdout
exec gunicorn -w 4 -b 0.0.0.0:5000 --access-logfile - --error-logfile - --log-level info app:app
