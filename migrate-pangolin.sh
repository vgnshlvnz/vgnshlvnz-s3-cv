#!/bin/bash
#
# Pangolin Reverse Proxy Migration Script
# Migrates /opt/entry from entry.vgnshlv.nz to new EC2 instance
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
OLD_SERVER="entry.vgnshlv.nz"
OLD_SERVER_USER="root"
OLD_SERVER_PASS="AlternateF13!"
NEW_SERVER_IP="43.217.104.44"
NEW_SERVER_USER="ubuntu"
SSH_KEY="~/.ssh/id_ed25519"
SOURCE_DIR="/opt/entry"
BACKUP_DIR="/tmp/pangolin-backup-$(date +%Y%m%d-%H%M%S)"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Pangolin Migration Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Old Server:${NC} $OLD_SERVER"
echo -e "${GREEN}New Server:${NC} $NEW_SERVER_IP"
echo ""

# Step 1: Wait for new instance SSH to be ready
echo -e "${BLUE}[1/6]${NC} Waiting for new instance SSH to be ready..."
RETRIES=0
MAX_RETRIES=30

while [ $RETRIES -lt $MAX_RETRIES ]; do
    if ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
        "${NEW_SERVER_USER}@${NEW_SERVER_IP}" "echo 'SSH Ready'" 2>/dev/null; then
        echo -e "${GREEN}✓ SSH is ready!${NC}"
        break
    fi
    RETRIES=$((RETRIES + 1))
    echo "  Attempt $RETRIES/$MAX_RETRIES... waiting 10s"
    sleep 10
done

if [ $RETRIES -eq $MAX_RETRIES ]; then
    echo -e "${RED}✗ SSH not ready after $MAX_RETRIES attempts${NC}"
    exit 1
fi

# Step 2: Create backup directory on new server
echo -e "${BLUE}[2/6]${NC} Creating backup directory on new server..."
ssh -i "$SSH_KEY" "${NEW_SERVER_USER}@${NEW_SERVER_IP}" \
    "sudo mkdir -p /opt && sudo chown ubuntu:ubuntu /opt"
echo -e "${GREEN}✓ Directory created${NC}"

# Step 3: Create local backup from old server using sshpass
echo -e "${BLUE}[3/6]${NC} Creating backup from old server..."

if ! command -v sshpass &> /dev/null; then
    echo -e "${YELLOW}⚠ sshpass not found. Installing...${NC}"
    sudo apt update && sudo apt install -y sshpass
fi

mkdir -p "$BACKUP_DIR"

echo "  Copying $SOURCE_DIR from $OLD_SERVER..."
# Security: Use SSH key authentication instead of password authentication
# To set up SSH keys: ssh-copy-id ${OLD_SERVER_USER}@${OLD_SERVER}
if [ -n "$OLD_SERVER_PASS" ]; then
    # If OLD_SERVER_PASS env var is set, use it (for backward compatibility)
    sshpass -p "$OLD_SERVER_PASS" \
        rsync -avz --progress \
        -e "ssh -o StrictHostKeyChecking=no" \
        "${OLD_SERVER_USER}@${OLD_SERVER}:${SOURCE_DIR}/" \
        "$BACKUP_DIR/"
else
    # Recommended: Use SSH key-based authentication (no password needed)
    rsync -avz --progress \
        -e "ssh -o StrictHostKeyChecking=no" \
        "${OLD_SERVER_USER}@${OLD_SERVER}:${SOURCE_DIR}/" \
        "$BACKUP_DIR/"
fi

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Backup created: $BACKUP_DIR${NC}"
    echo "  Files backed up:"
    ls -lah "$BACKUP_DIR" | head -20
else
    echo -e "${RED}✗ Backup failed${NC}"
    exit 1
fi

# Step 4: Transfer backup to new server
echo -e "${BLUE}[4/6]${NC} Transferring to new server..."
rsync -avz --progress \
    -e "ssh -i $SSH_KEY" \
    "$BACKUP_DIR/" \
    "${NEW_SERVER_USER}@${NEW_SERVER_IP}:/opt/entry/"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Files transferred successfully${NC}"
else
    echo -e "${RED}✗ Transfer failed${NC}"
    exit 1
fi

# Step 5: Verify on new server
echo -e "${BLUE}[5/6]${NC} Verifying files on new server..."
ssh -i "$SSH_KEY" "${NEW_SERVER_USER}@${NEW_SERVER_IP}" \
    "ls -lah /opt/entry | head -20"

FILE_COUNT=$(ssh -i "$SSH_KEY" "${NEW_SERVER_USER}@${NEW_SERVER_IP}" \
    "find /opt/entry -type f | wc -l")
echo -e "${GREEN}✓ Files on new server: $FILE_COUNT${NC}"

# Step 6: Set up Pangolin on new server
echo -e "${BLUE}[6/6]${NC} Setting up Pangolin..."

ssh -i "$SSH_KEY" "${NEW_SERVER_USER}@${NEW_SERVER_IP}" << 'REMOTE_SCRIPT'
#!/bin/bash
set -e

echo "Installing dependencies..."
sudo apt update
sudo apt install -y docker.io docker-compose git nginx

echo "Starting Docker..."
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker ubuntu

echo "Checking Pangolin configuration..."
if [ -f /opt/entry/docker-compose.yml ]; then
    echo "✓ docker-compose.yml found"
    cat /opt/entry/docker-compose.yml | head -20
elif [ -f /opt/entry/pangolin.conf ]; then
    echo "✓ pangolin.conf found"
    cat /opt/entry/pangolin.conf | head -20
fi

echo "Setting permissions..."
sudo chown -R ubuntu:ubuntu /opt/entry
chmod +x /opt/entry/*.sh 2>/dev/null || true

echo "Setup complete!"
REMOTE_SCRIPT

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Migration Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}New Server Details:${NC}"
echo "  IP:  $NEW_SERVER_IP"
echo "  DNS: ec2-43-217-104-44.ap-southeast-5.compute.amazonaws.com"
echo "  SSH: ssh -i $SSH_KEY ubuntu@$NEW_SERVER_IP"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "1. SSH into new server and test Pangolin:"
echo "   ${GREEN}ssh -i $SSH_KEY ubuntu@$NEW_SERVER_IP${NC}"
echo ""
echo "2. Start Pangolin (if using Docker):"
echo "   ${GREEN}cd /opt/entry && docker-compose up -d${NC}"
echo ""
echo "3. Update DNS records to point to new IP:"
echo "   ${GREEN}entry.vgnshlv.nz → $NEW_SERVER_IP${NC}"
echo ""
echo "4. Verify reverse proxy is working"
echo ""
echo -e "${YELLOW}Local backup kept at:${NC} $BACKUP_DIR"
echo ""
