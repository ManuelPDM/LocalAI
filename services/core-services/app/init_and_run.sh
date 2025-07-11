#!/bin/sh
set -e
echo "Running database initializations for core-service..."
# Use flask shell to run db.init_db() within the app context
echo "import database; database.init_db()" | flask shell
echo "Starting Gunicorn server for core-service..."
exec gunicorn --workers 2 --bind 0.0.0.0:8000 "main:app"