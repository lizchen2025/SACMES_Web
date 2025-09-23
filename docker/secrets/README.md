# Docker Secrets

This directory contains secret files for secure deployment.

## Setup for Production

1. Replace the example files with your actual secrets:
   ```bash
   # Generate secure random passwords
   openssl rand -base64 32 > redis_password.txt
   openssl rand -base64 48 > secret_key.txt
   openssl rand -base64 32 > agent_auth_token.txt
   ```

2. Set proper file permissions:
   ```bash
   chmod 600 *.txt
   ```

3. Never commit actual secret files to git!

## Secret Files

- `redis_password.txt` - Redis authentication password
- `secret_key.txt` - Flask session encryption key
- `agent_auth_token.txt` - Agent authentication token

## Security Notes

- Use strong, randomly generated passwords
- Rotate secrets regularly
- Monitor access to secret files
- Use proper file permissions (600)
- Consider using external secret management in production (Vault, etc.)