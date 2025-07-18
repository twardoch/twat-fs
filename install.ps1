# this_file: install.ps1

# PowerShell install script for twat-fs
# Downloads and installs the latest binary release on Windows

param(
    [string]$InstallDir = "$env:USERPROFILE\.local\bin",
    [switch]$Force
)

# Configuration
$REPO = "twardoch/twat-fs"
$BINARY_NAME = "twat-fs.exe"

# Colors for output
$GREEN = "Green"
$YELLOW = "Yellow"
$RED = "Red"

# Functions
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $GREEN
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor $YELLOW
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $RED
    exit 1
}

# Get latest release info
function Get-LatestRelease {
    Write-Info "Fetching latest release information..."
    
    $apiUrl = "https://api.github.com/repos/$REPO/releases/latest"
    
    try {
        $response = Invoke-RestMethod -Uri $apiUrl -Method Get
        return $response
    } catch {
        Write-Error "Failed to fetch release information: $($_.Exception.Message)"
    }
}

# Download and install binary
function Install-Binary {
    param([object]$ReleaseInfo)
    
    Write-Info "Installing for Windows platform"
    
    # Find download URL for Windows binary
    $asset = $ReleaseInfo.assets | Where-Object { $_.name -eq $BINARY_NAME }
    
    if (-not $asset) {
        Write-Error "Could not find Windows binary in release assets"
    }
    
    $downloadUrl = $asset.browser_download_url
    Write-Info "Downloading from: $downloadUrl"
    
    # Create install directory
    if (-not (Test-Path $InstallDir)) {
        New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    }
    
    # Download binary
    $installPath = Join-Path $InstallDir $BINARY_NAME
    
    if ((Test-Path $installPath) -and -not $Force) {
        Write-Warn "Binary already exists at $installPath. Use -Force to overwrite."
        $response = Read-Host "Overwrite existing installation? (y/N)"
        if ($response.ToLower() -ne 'y') {
            Write-Info "Installation cancelled."
            return
        }
    }
    
    try {
        Invoke-WebRequest -Uri $downloadUrl -OutFile $installPath
        Write-Info "Installed to: $installPath"
    } catch {
        Write-Error "Failed to download binary: $($_.Exception.Message)"
    }
    
    # Test installation
    try {
        $versionOutput = & $installPath version
        Write-Info "Installation successful!"
        Write-Host $versionOutput
    } catch {
        Write-Error "Installation failed - binary test failed"
    }
    
    # Add to PATH instructions
    $pathEnv = [Environment]::GetEnvironmentVariable("PATH", "User")
    if ($pathEnv -notlike "*$InstallDir*") {
        Write-Warn "Add $InstallDir to your PATH to use twat-fs from anywhere:"
        Write-Host "  Run this command in PowerShell as Administrator:"
        Write-Host "  [Environment]::SetEnvironmentVariable('PATH', `"$InstallDir;`$([Environment]::GetEnvironmentVariable('PATH', 'User'))`", 'User')"
    }
}

# Main installation function
function Main {
    Write-Info "Installing twat-fs..."
    
    # Check PowerShell version
    if ($PSVersionTable.PSVersion.Major -lt 3) {
        Write-Error "PowerShell 3.0 or higher is required"
    }
    
    # Get latest release
    $releaseInfo = Get-LatestRelease
    
    # Install binary
    Install-Binary $releaseInfo
    
    Write-Info "Installation complete!"
}

# Run main function
Main