#!/bin/sh

# Wait for the database to be ready
echo "Waiting for postgres..."
while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
  sleep 0.1
done
echo "PostgreSQL started"

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --no-input

# Start server
echo "Starting server..."
daphne -b 0.0.0.0 -p 8000 tournament_project.asgi:application
