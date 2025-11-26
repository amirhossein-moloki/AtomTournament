# Use the official Nginx image as a base
FROM nginx:1.25-alpine

# Install necessary packages
# - inotify-tools: for monitoring filesystem events (certificate renewals)
# - openssl: for generating a self-signed certificate for initial startup
# - gettext: for `envsubst` to substitute environment variables in the config template
RUN apk add --no-cache inotify-tools openssl gettext

# Copy the entrypoint script and the Nginx configuration template
COPY ./entrypoint.sh /usr/local/bin/entrypoint.sh
COPY ./app.conf.template /etc/nginx/templates/app.conf.template

# Make the entrypoint script executable
RUN chmod +x /usr/local/bin/entrypoint.sh

# The entrypoint will generate the final config and start Nginx
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Expose ports
EXPOSE 80 443

# The command to run when the container starts.
# The entrypoint script will execute this command after setting up the configuration.
CMD ["nginx", "-g", "daemon off;"]
