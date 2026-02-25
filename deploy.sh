#!/bin/bash
# Life Systems Deployment Script

set -e

echo "🚀 Deploying Life Systems..."

# 1. Stop existing service if running
if systemctl is-active --quiet life-systems; then
    echo "Stopping existing service..."
    sudo systemctl stop life-systems
fi

# 2. Copy files to /opt/life-systems
echo "Copying files to /opt/life-systems..."
sudo mkdir -p /opt/life-systems
sudo cp -r * /opt/life-systems/
sudo chown -R ubuntu:ubuntu /opt/life-systems

# 3. Create venv and install dependencies
echo "Setting up Python environment..."
cd /opt/life-systems
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Initialize database
echo "Initializing database..."
sudo mkdir -p /var/lib/life-systems
sudo chown ubuntu:ubuntu /var/lib/life-systems
python3 -m database.db

# 5. Install systemd service
echo "Installing systemd service..."
sudo cp life-systems.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable life-systems
sudo systemctl start life-systems

# 6. Configure Caddy
echo "Configuring Caddy..."
sudo mkdir -p /var/log/caddy
sudo chown caddy:caddy /var/log/caddy
sudo cp Caddyfile /etc/caddy/Caddyfile
sudo systemctl restart caddy

echo "✅ Deployment complete!"
echo ""
echo "Service status:"
systemctl status life-systems --no-pager | head -10
echo ""
systemctl status caddy --no-pager | head -10
echo ""
echo "🌐 Service available at: https://life.plocha.eu"
echo "📊 Test: curl -u jurek:LifeSystems2026! https://life.plocha.eu/api/health"
