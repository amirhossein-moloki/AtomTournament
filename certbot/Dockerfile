FROM certbot/certbot:latest

# Install netcat (nc) to check for Nginx availability
RUN apk add --no-cache netcat-openbsd

# Set the entrypoint for the container
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]
