# Automated Nginx and Certbot SSL Setup

This project provides a fully automated setup for Nginx and Certbot to obtain and renew SSL certificates using Docker Compose. The architecture is designed to be robust, avoiding common race conditions and dependency issues.

## Features

- **Fully Automated:** SSL certificates are obtained and renewed automatically.
- **Decoupled Services:** Nginx and Certbot run independently, without direct dependencies.
- **Graceful Reloads:** Nginx reloads its configuration without downtime.
- **Robust Startup:** Nginx starts up even without an initial SSL certificate, enabling Certbot to perform the initial challenge.
- **Easy Configuration:** Simple setup using a `.env` file.

## Prerequisites

- Docker
- Docker Compose
- A registered domain name pointing to your server's IP address.
- Ports 80 and 443 open on your server's firewall.

## How It Works

This setup uses an intelligent Nginx entrypoint script that decouples it from the Certbot container.

1.  **Nginx Startup:** The Nginx container starts and its entrypoint script checks for the existence of an SSL certificate.
    *   **If no certificate is found:** It generates a temporary, HTTP-only configuration that serves a placeholder page and allows Certbot's ACME challenge requests to pass through.
    *   **If a certificate is found:** It generates a production-ready configuration that redirects all HTTP traffic to HTTPS and enables SSL.

2.  **Certbot Operation:** The Certbot container runs independently. Its entrypoint script periodically attempts to obtain or renew the SSL certificate for the specified domain using the webroot method. The challenge files are written to a shared volume that Nginx can access.

3.  **Automatic Nginx Reload:** The Nginx entrypoint script also starts a background process that monitors the certificate directory for changes (using `inotifywait`). When Certbot successfully obtains or renews a certificate, this monitor detects the change and triggers a graceful `nginx -s reload`, loading the new certificate and updated configuration without any downtime.

## Configuration

1.  **Create a `.env` file:**

    Copy the example file:
    ```bash
    cp .env.example .env
    ```

2.  **Edit the `.env` file:**

    Open the `.env` file and replace the placeholder values with your domain and email address.

    ```ini
    DOMAIN=your-domain.com
    EMAIL=your-email@example.com
    ```

## Usage

To start the services, run the following command from the root of the project:

```bash
docker compose up -d
```

### Initial Certificate Acquisition

On the first run, Certbot may take a minute or two to obtain the certificate. You can monitor its progress by checking the logs:

```bash
docker compose logs -f certbot
```

Once the certificate is obtained, the Nginx container will automatically detect it and reload its configuration to enable HTTPS. You can see this in the Nginx logs:

```bash
docker compose logs -f nginx
```

### Forcing Certificate Renewal

To manually trigger a renewal attempt, you can run:

```bash
docker compose exec certbot /usr/local/bin/entrypoint.sh
```

## File Structure

```
.
├── .env.example        # Example environment variables
├── .gitignore          # Files to be ignored by Git
├── README.md           # This file
├── certbot/
│   └── entrypoint.sh   # Certbot's script for obtaining/renewing certificates
├── docker-compose.yml  # Docker Compose file defining the services and volumes
└── nginx/
    ├── Dockerfile          # Dockerfile for the custom Nginx image
    ├── app.conf.template   # Nginx configuration template
    └── entrypoint.sh       # The intelligent Nginx entrypoint script
```
