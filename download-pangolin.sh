#!/bin/bash
set -e

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="/tmp/pangolin-backup-${TIMESTAMP}"

mkdir -p "${BACKUP_DIR}"
echo "Created: ${BACKUP_DIR}"

echo "Downloading /opt/entry from entry.vgnshlv.nz..."
# Security: Use SSH key authentication instead of password authentication
# To set up SSH keys: ssh-copy-id root@entry.vgnshlv.nz
if [ -n "$SSH_PASSWORD" ]; then
    # If SSH_PASSWORD env var is set, use it (for backward compatibility)
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no root@entry.vgnshlv.nz "cd /opt && tar czf - entry" | tar xzf - -C "${BACKUP_DIR}"
else
    # Recommended: Use SSH key-based authentication (no password needed)
    ssh -o StrictHostKeyChecking=no root@entry.vgnshlv.nz "cd /opt && tar czf - entry" | tar xzf - -C "${BACKUP_DIR}"
fi

echo "Download complete!"
ls -lah "${BACKUP_DIR}/entry"
echo ""
echo "Backup location: ${BACKUP_DIR}/entry"
