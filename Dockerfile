# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    netcat-openbsd \
    locales \
    && rm -rf /var/lib/apt/lists/*

# Generate locale
RUN echo "fa_IR.UTF-8 UTF-8" > /etc/locale.gen && \
    locale-gen

# Set environment variables for locale
ENV LANG fa_IR.UTF-8
ENV LANGUAGE fa_IR:fa
ENV LC_ALL fa_IR.UTF-8

# Install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Expose port for daphne
EXPOSE 8000
