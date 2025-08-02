#!/bin/sh

# Wait for the database to be ready
echo "Waiting for postgres..."
while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
  sleep 0.1
done
echo "PostgreSQL started"

# The first argument is the service type
service_type=$1
shift # remove the first argument

# If the service is "web", then run migrations and collect static
if [ "$service_type" = "web" ]; then
    echo "Running database migrations..."
    python manage.py migrate --no-input

    echo "Collecting static files..."
    python manage.py collectstatic --no-input
fi

# Execute the rest of the command
exec "$@"
