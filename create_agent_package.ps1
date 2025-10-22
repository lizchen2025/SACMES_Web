# SACMES Agent Packaging Script

Write-Host "========================================"
Write-Host "SACMES Agent Packager"
Write-Host "========================================"
Write-Host ""

# Clean up old files
if (Test-Path 'agent_package') {
    Write-Host "Removing old package directory..."
    Remove-Item -Recurse -Force 'agent_package'
}

if (Test-Path 'SACMES_Agent.zip') {
    Write-Host "Removing old ZIP file..."
    Remove-Item -Force 'SACMES_Agent.zip'
}

# Create package directory
Write-Host "Creating package directory..."
New-Item -ItemType Directory -Path 'agent_package' | Out-Null

# Copy files
Write-Host ""
Write-Host "Copying files..."
Write-Host ""

Write-Host "[1/6] agent.py"
Copy-Item 'agent.py' 'agent_package\'

Write-Host "[2/6] start_agent.bat"
Copy-Item 'start_agent.bat' 'agent_package\'

Write-Host "[3/6] install_python.bat"
Copy-Item 'install_python.bat' 'agent_package\'

Write-Host "[4/6] test_installation.bat"
Copy-Item 'test_installation.bat' 'agent_package\'

Write-Host "[5/6] Netzlab.ico"
Copy-Item 'Netzlab.ico' 'agent_package\'

Write-Host "[6/6] AGENT_README.txt (as README.txt)"
Copy-Item 'AGENT_README.txt' 'agent_package\README.txt'

# Create ZIP
Write-Host ""
Write-Host "Creating ZIP archive..."
Compress-Archive -Path 'agent_package\*' -DestinationPath 'SACMES_Agent.zip' -Force

# Clean up temp directory
Write-Host "Cleaning up..."
Remove-Item -Recurse -Force 'agent_package'

# Show results
Write-Host ""
Write-Host "========================================"
Write-Host "Package Created Successfully!"
Write-Host "========================================"
Write-Host ""
Write-Host "File: SACMES_Agent.zip"
Write-Host ""

$sizeKB = [math]::Round((Get-Item 'SACMES_Agent.zip').Length / 1KB, 2)
Write-Host "Size: $sizeKB KB"

Write-Host ""
Write-Host "Contents:"
Write-Host "- agent.py (Agent source code)"
Write-Host "- start_agent.bat (Main launcher)"
Write-Host "- install_python.bat (Robust first-time setup)"
Write-Host "- test_installation.bat (Installation verification)"
Write-Host "- Netzlab.ico (Application icon)"
Write-Host "- README.txt (User documentation)"
Write-Host ""
Write-Host "This ZIP is ready for distribution!"
Write-Host "Users can extract and run start_agent.bat to begin."
Write-Host ""
