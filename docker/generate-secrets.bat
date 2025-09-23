@echo off
REM Script to generate secure secrets for SACMES deployment on Windows
REM Usage: generate-secrets.bat

set SECRETS_DIR=secrets

echo 🔐 Generating secure secrets for SACMES deployment...

REM Create secrets directory if it doesn't exist
if not exist "%SECRETS_DIR%" mkdir "%SECRETS_DIR%"

echo Generating Redis password...
powershell -Command "[System.Web.Security.Membership]::GeneratePassword(32, 8)" > "%SECRETS_DIR%\redis_password.txt"

echo Generating Flask secret key...
powershell -Command "[System.Web.Security.Membership]::GeneratePassword(48, 12)" > "%SECRETS_DIR%\secret_key.txt"

echo Generating agent authentication token...
powershell -Command "[System.Web.Security.Membership]::GeneratePassword(32, 8)" > "%SECRETS_DIR%\agent_auth_token.txt"

echo ✅ Secrets generated successfully in %SECRETS_DIR%\
echo.
echo 📁 Generated files:
dir "%SECRETS_DIR%\*.txt"
echo.
echo ⚠️  IMPORTANT SECURITY NOTES:
echo    - Never commit these secret files to git!
echo    - Store them securely and rotate regularly
echo    - Use different secrets for each environment
echo    - Consider using external secret management in production
echo.
echo 🚀 Ready to deploy with docker-compose up -d

pause