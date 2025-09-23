#!/bin/bash

# Script to generate secure secrets for SACMES deployment
# Usage: ./generate-secrets.sh

SECRETS_DIR="./secrets"

echo "🔐 Generating secure secrets for SACMES deployment..."

# Create secrets directory if it doesn't exist
mkdir -p "$SECRETS_DIR"

# Generate Redis password (32 characters)
echo "Generating Redis password..."
openssl rand -base64 32 | tr -d "=+/" | cut -c1-32 > "$SECRETS_DIR/redis_password.txt"

# Generate Flask secret key (48 characters for extra security)
echo "Generating Flask secret key..."
openssl rand -base64 48 | tr -d "=+/" | cut -c1-48 > "$SECRETS_DIR/secret_key.txt"

# Generate agent authentication token (32 characters)
echo "Generating agent authentication token..."
openssl rand -base64 32 | tr -d "=+/" | cut -c1-32 > "$SECRETS_DIR/agent_auth_token.txt"

# Set secure file permissions
chmod 600 "$SECRETS_DIR"/*.txt

echo "✅ Secrets generated successfully in $SECRETS_DIR/"
echo ""
echo "📁 Generated files:"
ls -la "$SECRETS_DIR"/*.txt
echo ""
echo "🔒 File permissions set to 600 (owner read/write only)"
echo ""
echo "⚠️  IMPORTANT SECURITY NOTES:"
echo "   - Never commit these secret files to git!"
echo "   - Store them securely and rotate regularly"
echo "   - Use different secrets for each environment"
echo "   - Consider using external secret management in production"
echo ""
echo "🚀 Ready to deploy with docker-compose up -d"