#!/bin/bash
# Life Systems Deployment Script

set -e

echo "=== Life Systems Deployment ==="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo "❌ Do not run as root. Run as ubuntu user with sudo access."
    exit 1
fi

# Step 1: Copy files to /opt/life-systems
echo "📁 Copying files to /opt/life-systems..."
sudo mkdir -p /opt/life-systems
sudo rsync -av --exclude='.git' --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' . /opt/life-systems/
sudo chown -R ubuntu:ubuntu /opt/life-systems
cd /opt/life-systems

# Step 1.5: Create virtualenv and install dependencies
echo "📦 Installing Python dependencies..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt

# Step 2: Initialize database
echo "🗄️  Initializing database..."
sudo mkdir -p /var/lib/life-systems
python3 -c "from api.database import init_db; init_db('/var/lib/life-systems/life.db')"
sudo chown ubuntu:ubuntu /var/lib/life-systems/life.db
sudo chmod 600 /var/lib/life-systems/life.db

# Step 3: Setup environment file
echo "🔐 Setting up environment..."
if [ ! -f /etc/life-systems/env ]; then
    sudo mkdir -p /etc/life-systems
    sudo cp .env.example /etc/life-systems/env
    sudo chmod 600 /etc/life-systems/env
    echo "⚠️  Edit /etc/life-systems/env with your credentials:"
    echo "    - ANTHROPIC_API_KEY"
    echo "    - LS_USER / LS_PASSWORD"
    echo "    - SLACK_BOT_TOKEN (optional)"
    echo ""
    read -p "Press Enter after editing /etc/life-systems/env..."
else
    echo "✓ Environment file exists"
fi

# Step 3.5: Install Caddy
echo "🌐 Installing/configuring Caddy..."
if ! command -v caddy &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
    sudo apt-get update
    sudo apt-get install -y caddy
else
    echo "✓ Caddy already installed"
fi

sudo mkdir -p /var/log/caddy
sudo chown -R caddy:caddy /var/log/caddy
sudo cp Caddyfile /etc/caddy/Caddyfile
sudo systemctl enable caddy
sudo systemctl restart caddy

# Step 4: Install systemd services
echo "⚙️  Installing systemd services..."
sudo cp systemd/life-systems.service /etc/systemd/system/
sudo cp systemd/life-systems-scanner.service /etc/systemd/system/
sudo cp systemd/life-systems-scanner.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable life-systems
sudo systemctl enable life-systems-scanner.timer

# Step 5: Start services
echo "🚀 Starting services..."
sudo systemctl restart life-systems
sudo systemctl start life-systems-scanner.timer

# Step 6: Check status
echo ""
echo "=== Service Status ==="
sudo systemctl status life-systems --no-pager -l
echo ""
echo "=== Scanner Timer Status ==="
systemctl list-timers | grep life-systems

# Step 7: Test API
echo ""
echo "=== Testing API ==="
sleep 2
if curl -s http://localhost:8000/api/health | grep -q '"status":"ok"'; then
    echo "✅ API is responding"
else
    echo "❌ API not responding. Check logs:"
    echo "   sudo journalctl -u life-systems -n 50"
fi

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "🌐 Service: https://life.plocha.eu"
echo "📚 API Docs: https://life.plocha.eu/docs"
echo "📝 Logs: sudo journalctl -u life-systems -f"
echo "🔐 Credentials: jurek / LifeSystems2026!"
echo ""
echo "Next steps:"
echo "1. Test: curl -u jurek:LifeSystems2026! https://life.plocha.eu/api/health"
echo "2. Run first scan: sudo systemctl start life-systems-scanner"
echo "3. Check scanner timer: systemctl list-timers | grep life-systems"
