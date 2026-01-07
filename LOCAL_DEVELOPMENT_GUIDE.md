# Local Development Environment Setup Guide

This guide provides step-by-step instructions for setting up a local development environment for this project without using Docker.

## 1. Prerequisites

Before you begin, ensure you have the following installed on your system:
- Git
- Python (version 3.10 or higher)
- `pip` (Python package installer)
- `sudo` or administrator privileges

## 2. Clone the Repository

First, clone the project repository to your local machine:

```bash
git clone <repository-url>
cd <project-directory>
```

## 3. Install Python Dependencies

Install all the required Python packages using `pip` and the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

## 4. Set Up PostgreSQL Database

The application requires a PostgreSQL database to store its data.

### 4.1. Install PostgreSQL

If you don't have PostgreSQL installed, use your system's package manager. For Debian/Ubuntu-based systems:

```bash
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib
```

### 4.2. Start the PostgreSQL Service

Once installed, start and enable the PostgreSQL service:

```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 4.3. Create Database and User

You need to create a dedicated user and database for the application. Access the `psql` shell as the `postgres` user:

```bash
sudo -u postgres psql
```

Then, run the following SQL commands to create a user and a database. Replace `yourdbuser` and `yourdbpassword` with your desired credentials.

```sql
CREATE USER yourdbuser WITH PASSWORD 'yourdbpassword';
CREATE DATABASE yourdbname OWNER yourdbuser;
\q
```

## 5. Set Up Redis

Redis is used as a message broker for Celery and for caching.

### 5.1. Install Redis

For Debian/Ubuntu-based systems:
```bash
sudo apt-get update
sudo apt-get install -y redis-server
```

### 5.2. Start Redis Server

Start the Redis server. You can run it in the background.
```bash
redis-server &
```

## 6. Configure Environment Variables

The application is configured using a `.env` file.

### 6.1. Create the `.env` file

Copy the example environment file:
```bash
cp env.example .env
```

### 6.2. Update the `.env` file for Local Setup

Open the newly created `.env` file and modify the following variables to point to your local PostgreSQL and Redis instances.

- **`POSTGRES_HOST`**: Change from `db` to `localhost`.
- **`DATABASE_URL`**: Update with the credentials you created in step 4.3.
- **`REDIS_URL`**: Change from `redis` to `localhost`.

Your file should look like this (other variables can be left as default for now):

```ini
# ... other settings

# Database
POSTGRES_DB=yourdbname
POSTGRES_USER=yourdbuser
POSTGRES_PASSWORD=yourdbpassword
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
DATABASE_URL="postgres://yourdbuser:yourdbpassword@localhost:5432/yourdbname"

# Redis
REDIS_URL="redis://localhost:6379/0"

# ... other settings
```

## 7. Run Database Migrations

With the database and environment configured, apply the database schema migrations:

```bash
python manage.py migrate
```

## 8. Run Celery Services

The application uses Celery for background tasks, such as publishing scheduled posts. You need to run both the Celery beat (scheduler) and a worker.

### 8.1. Start the Celery Beat

Open a new terminal window/tab and run the following command to start the scheduler:

```bash
celery -A tournament_project beat -l info &
```

### 8.2. Start the Celery Worker

In another terminal window/tab, start a worker to execute the tasks:

```bash
celery -A tournament_project worker -l info -Q default &
```

## 9. Run the Development Server

Finally, you can run the Django development server:

```bash
python manage.py runserver
```

Your local development environment is now set up and running! You can access the application at `http://127.0.0.1:8000`.
