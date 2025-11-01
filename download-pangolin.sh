#!/bin/bash
set -e

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="/tmp/pangolin-backup-${TIMESTAMP}"

mkdir -p "${BACKUP_DIR}"
echo "Created: ${BACKUP_DIR}"

echo "Downloading /opt/entry from entry.vgnshlv.nz..."
sshpass -p 'AlternateF13!' ssh -o StrictHostKeyChecking=no root@entry.vgnshlv.nz "cd /opt && tar czf - entry" | tar xzf - -C "${BACKUP_DIR}"

echo "Download complete!"
ls -lah "${BACKUP_DIR}/entry"
echo ""
echo "Backup location: ${BACKUP_DIR}/entry"
