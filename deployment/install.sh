#!/bin/bash

# ==============================================================================
# Full Backup System Installer (PostgreSQL + Files)
# Using WAL-G for PostgreSQL and Restic for Files on Google Cloud Storage
# ==============================================================================
# This script automates the setup of a full backup system.
# It installs WAL-G, Restic, and sets up systemd services for automated
# backups and retention for both database and application files.
#
# !! IMPORTANT !!
# This script must be run with root privileges (e.g., using sudo).
# ==============================================================================

set -e
set -o pipefail

# --- Configuration ---
WALG_VERSION="v2.1.2"
RESTIC_VERSION="0.16.4" # Check for the latest version
DEPLOYMENT_FILES_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# --- Helper Functions ---
echo_info() {
    echo "[INFO] $1"
}

echo_success() {
    echo "[SUCCESS] $1"
}

echo_warning() {
    echo "[WARNING] $1"
}

echo_error() {
    echo "[ERROR] $1"
    exit 1
}

# --- Pre-flight Checks ---
# Check if running as root
if [[ "${EUID}" -ne 0 ]]; then
    echo_error "This script must be run as root. Please use sudo."
fi


# --- Main Installation ---
main() {
    echo_info "Starting Full Backup System installation..."

    # 1. Install prerequisites
    echo_info "Installing prerequisite packages (curl, pv, bzip2)..."
    apt-get update > /dev/null
    apt-get install -y curl pv bzip2
    echo_success "Prerequisites installed."

    # 2. Download and install WAL-G
    echo_info "Downloading and installing WAL-G version ${WALG_VERSION}..."
    cd /tmp
    curl -L "https://github.com/wal-g/wal-g/releases/download/${WALG_VERSION}/wal-g-pg-ubuntu-22.04-amd64.tar.gz" -o wal-g.tar.gz
    tar -zxvf wal-g.tar.gz
    mv wal-g-pg-ubuntu-22.04-amd64/wal-g /usr/local/bin/
    rm -rf wal-g.tar.gz wal-g-pg-ubuntu-22.04-amd64
    echo_success "WAL-G installed successfully."
    echo_info "WAL-G version: $(wal-g --version)"

    # 3. Download and install Restic
    echo_info "Downloading and installing Restic version ${RESTIC_VERSION}..."
    cd /tmp
    curl -L "https://github.com/restic/restic/releases/download/v${RESTIC_VERSION}/restic_${RESTIC_VERSION}_linux_amd64.bz2" -o restic.bz2
    bzip2 -d restic.bz2
    mv restic_${RESTIC_VERSION}_linux_amd64 /usr/local/bin/restic
    chmod +x /usr/local/bin/restic
    rm -f restic.bz2
    echo_success "Restic installed successfully."
    echo_info "Restic version: $(restic version)"

    # 4. Create configuration directories
    echo_info "Creating configuration directory /etc/wal-g/..."
    mkdir -p /etc/wal-g/
    chown -R postgres:postgres /etc/wal-g/
    echo_success "WAL-G configuration directory created."

    echo_info "Creating configuration directory /etc/restic/..."
    mkdir -p /etc/restic/
    # No specific user, root will run this, but the file inside should be protected.
    echo_success "Restic configuration directory created."

    # 5. Install systemd units
    echo_info "Installing all systemd service and timer files..."
    cp "${DEPLOYMENT_FILES_DIR}/walg-backup.service" /etc/systemd/system/
    cp "${DEPLOYMENT_FILES_DIR}/walg-backup.timer" /etc/systemd/system/
    cp "${DEPLOYMENT_FILES_DIR}/walg-retain.service" /etc/systemd/system/
    cp "${DEPLOYMENT_FILES_DIR}/walg-retain.timer" /etc/systemd/system/
    cp "${DEPLOYMENT_FILES_DIR}/restic-backup.service" /etc/systemd/system/
    cp "${DEPLOYMENT_FILES_DIR}/restic-backup.timer" /etc/systemd/system/
    cp "${DEPLOYMENT_FILES_DIR}/restic-prune.service" /etc/systemd/system/
    cp "${DEPLOYMENT_FILES_DIR}/restic-prune.timer" /etc/systemd/system/
    echo_success "All systemd files installed."

    # 6. Reload systemd and enable timers
    echo_info "Reloading systemd daemon and enabling all timers..."
    systemctl daemon-reload
    systemctl enable walg-backup.timer
    systemctl enable walg-retain.timer
    systemctl enable restic-backup.timer
    systemctl enable restic-prune.timer
    systemctl start walg-backup.timer
    systemctl start walg-retain.timer
    systemctl start restic-backup.timer
    systemctl start restic-prune.timer
    echo_success "All systemd timers enabled and started."
    echo_info "Current timer status:"
    systemctl list-timers | grep -E 'walg|restic'

    # --- Final Instructions ---
    echo ""
    echo_success "Installation complete!"
    echo "=============================================================================="
    echo_warning "ACTION REQUIRED: Please complete the following manual steps:"
    echo ""
    echo "--- PostgreSQL (WAL-G) ---"
    echo "1. CONFIGURE POSTGRESQL:"
    echo "   - Edit your postgresql.conf file using the guide provided in:"
    echo "     '${DEPLOYMENT_FILES_DIR}/postgres_config_guide.txt'"
    echo ""
    echo "2. CREATE WAL-G CONFIGURATION FILE:"
    echo "   - Copy '${DEPLOYMENT_FILES_DIR}/walg-base-config.env.template' to '/etc/wal-g/walg-base-config.env'"
    echo "   - Edit it and fill in your GCS bucket details."
    echo "   - Secure it: 'sudo chown postgres:postgres /etc/wal-g/walg-base-config.env && sudo chmod 600 /etc/wal-g/walg-base-config.env'"
    echo ""
    echo "3. ADD GCP KEY FOR WAL-G:"
    echo "   - Copy your GCS Service Account JSON key to '/etc/wal-g/gcs-key.json'"
    echo "   - Secure it: 'sudo chown postgres:postgres /etc/wal-g/gcs-key.json && sudo chmod 600 /etc/wal-g/gcs-key.json'"
    echo ""
    echo "4. RESTART POSTGRESQL:"
    echo "   - 'sudo systemctl restart postgresql'"
    echo ""
    echo "--- File System (Restic) ---"
    echo "5. CREATE RESTIC CONFIGURATION FILE:"
    echo "   - Copy '${DEPLOYMENT_FILES_DIR}/restic-env.template' to '/etc/restic/restic-env'"
    echo "   - Edit it and fill in your GCS bucket, repository password, and paths to back up."
    echo "   - Secure it: 'sudo chmod 600 /etc/restic/restic-env'"
    echo ""
    echo "6. ADD GCP KEY FOR RESTIC:"
    echo "   - Restic can use the same key as WAL-G. Point to it in the config file:"
    echo "     'export GOOGLE_APPLICATION_CREDENTIALS=/etc/wal-g/gcs-key.json'"
    echo ""
    echo "7. INITIALIZE RESTIC REPOSITORY:"
    echo "   - You MUST do this once before the first backup:"
    echo "     'sudo bash -c \". /etc/restic/restic-env && restic init\"'"
    echo ""
    echo "--- Final Testing ---"
    echo "8. RUN FIRST BACKUPS MANUALLY:"
    echo "   - WAL-G: 'sudo -u postgres bash -c \". /etc/wal-g/walg-base-config.env && wal-g backup-push /var/lib/postgresql/14/main\"'"
    echo "   - Restic: 'sudo bash -c \". /etc/restic/restic-env && restic backup \$(cat /etc/restic/paths-to-backup.txt)\"'"
    echo "=============================================================================="
}

# --- Run main function ---
main
