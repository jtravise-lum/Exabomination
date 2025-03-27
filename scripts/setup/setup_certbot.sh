#!/bin/bash
# Script to obtain and configure SSL certificate from Let's Encrypt using Certbot

# Set colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

DOMAIN="exp.travise.net"
EMAIL="your.email@example.com"  # Replace with your email

echo -e "${YELLOW}Setting up SSL certificate for ${DOMAIN}${NC}"

# Check if Certbot is installed
if ! command -v certbot &> /dev/null; then
    echo -e "${YELLOW}Certbot not found. Installing...${NC}"
    sudo apt-get update
    sudo apt-get install -y certbot
fi

# Stop Caddy temporarily to free up port 80
echo -e "${YELLOW}Stopping Caddy service...${NC}"
sudo systemctl stop caddy

# Obtain certificate using standalone mode
echo -e "${YELLOW}Obtaining certificate from Let's Encrypt...${NC}"
sudo certbot certonly --standalone --preferred-challenges http \
    -d ${DOMAIN} \
    --email ${EMAIL} \
    --agree-tos \
    --non-interactive

# Check if certificate was obtained successfully
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to obtain certificate. Check the error message above.${NC}"
    sudo systemctl start caddy
    exit 1
fi

echo -e "${GREEN}Certificate obtained successfully!${NC}"

# Update Caddyfile to use the Let's Encrypt certificate
echo -e "${YELLOW}Updating Caddyfile to use the new certificate...${NC}"
CERT_PATH="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
KEY_PATH="/etc/letsencrypt/live/${DOMAIN}/privkey.pem"

# Create a backup of the original Caddyfile
cp Caddyfile Caddyfile.bak

# Replace the tls internal line with the path to the certificates
sed -i "s|tls internal|tls ${CERT_PATH} ${KEY_PATH}|" Caddyfile

# Grant Caddy permission to read the certificate files
echo -e "${YELLOW}Granting Caddy permission to read certificate files...${NC}"
sudo setfacl -R -m u:caddy:rX /etc/letsencrypt/live
sudo setfacl -R -m u:caddy:rX /etc/letsencrypt/archive

# Restart Caddy
echo -e "${YELLOW}Starting Caddy service...${NC}"
sudo systemctl start caddy

# Display status
echo -e "${GREEN}SSL certificate setup complete!${NC}"
echo -e "${YELLOW}Certificate will expire in 90 days. Remember to renew it before expiration.${NC}"
echo -e "${YELLOW}To renew all certificates, run: sudo certbot renew${NC}"

# Create Certbot renewal hook for Caddy
echo -e "${YELLOW}Setting up auto-renewal hook for Caddy...${NC}"
sudo mkdir -p /etc/letsencrypt/renewal-hooks/post

sudo tee /etc/letsencrypt/renewal-hooks/post/reload-caddy > /dev/null << 'EOF'
#!/bin/bash
systemctl reload caddy
EOF

sudo chmod +x /etc/letsencrypt/renewal-hooks/post/reload-caddy

echo -e "${GREEN}Setup complete! Your site should now be available at https://${DOMAIN}${NC}"