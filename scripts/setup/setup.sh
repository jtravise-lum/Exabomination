#!/bin/bash

set -e

echo "Updating system..."
apt update && apt upgrade -y

echo "Installing core packages..."
apt install -y \
  python3 python3-pip python3-venv python3-dev \
  curl wget git vim ufw gnupg software-properties-common ca-certificates lsb-release fail2ban

echo "Locking down SSH (no root login, no password auth)..."
sed -i 's/^PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl reload ssh

echo "Configuring UFW..."
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw --force enable

echo "Enabling fail2ban..."
systemctl enable --now fail2ban

echo "Installing Docker and Compose plugin..."
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
usermod -aG docker "$USER"

echo "Installing Caddy (official)..."
apt install -y debian-keyring debian-archive-keyring
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | \
  gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg

curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | \
  tee /etc/apt/sources.list.d/caddy-stable.list

apt update
apt install -y caddy
systemctl enable caddy

echo "Creating placeholder Caddyfile..."
mkdir -p /etc/caddy/sites
touch /etc/caddy/Caddyfile
echo "# Drop your config here" > /etc/caddy/Caddyfile

echo "Cleaning up possible old config junk..."
rm -f /etc/apt/apt.conf.d/20listchanges /etc/apt/sources.list.d/deadsnakes-ubuntu-ppa*.list
apt purge -y apt-listchanges || true
apt autoremove -y
apt clean

echo
echo "✅ Setup complete. You may want to reboot before starting Docker/Caddy services."
