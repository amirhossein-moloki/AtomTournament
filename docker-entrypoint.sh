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

if [ "$SKIP_STATIC_PRECOMPRESS" != "1" ]; then
  echo "Pre-compressing static assets..."
  python scripts/precompress_static.py /app/staticfiles
else
  echo "Skipping static asset pre-compression (SKIP_STATIC_PRECOMPRESS=1)"
fi

# Start server
echo "Starting server..."
daphne -b 0.0.0.0 -p 8000 tournament_project.asgi:application
