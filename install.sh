#!/bin/bash
# this_file: install.sh

# Install script for twat-fs
# Downloads and installs the latest binary release

set -e

# Configuration
REPO="twardoch/twat-fs"
INSTALL_DIR="$HOME/.local/bin"
BINARY_NAME="twat-fs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Detect OS and architecture
detect_platform() {
    local os=$(uname -s)
    local arch=$(uname -m)
    
    case $os in
        Linux)
            echo "linux"
            ;;
        Darwin)
            echo "macos"
            ;;
        CYGWIN*|MINGW32*|MINGW64*|MSYS*)
            echo "windows"
            ;;
        *)
            error "Unsupported operating system: $os"
            ;;
    esac
}

# Get latest release info
get_latest_release() {
    log "Fetching latest release information..."
    
    local api_url="https://api.github.com/repos/$REPO/releases/latest"
    local release_info
    
    if command -v curl >/dev/null 2>&1; then
        release_info=$(curl -s "$api_url")
    elif command -v wget >/dev/null 2>&1; then
        release_info=$(wget -qO- "$api_url")
    else
        error "Neither curl nor wget is available. Please install one of them."
    fi
    
    echo "$release_info"
}

# Download and install binary
install_binary() {
    local platform=$(detect_platform)
    local release_info="$1"
    
    log "Detected platform: $platform"
    
    # Determine binary name based on platform
    local binary_filename="$BINARY_NAME"
    if [ "$platform" = "windows" ]; then
        binary_filename="$BINARY_NAME.exe"
    fi
    
    # Extract download URL
    local download_url
    if command -v jq >/dev/null 2>&1; then
        download_url=$(echo "$release_info" | jq -r ".assets[] | select(.name == \"$binary_filename\") | .browser_download_url")
    else
        # Fallback parsing without jq
        download_url=$(echo "$release_info" | grep -o "\"browser_download_url\":[^,]*$binary_filename\"" | cut -d'"' -f4)
    fi
    
    if [ -z "$download_url" ] || [ "$download_url" = "null" ]; then
        error "Could not find binary for platform: $platform"
    fi
    
    log "Downloading from: $download_url"
    
    # Create install directory
    mkdir -p "$INSTALL_DIR"
    
    # Download binary
    local temp_file=$(mktemp)
    if command -v curl >/dev/null 2>&1; then
        curl -L -o "$temp_file" "$download_url"
    elif command -v wget >/dev/null 2>&1; then
        wget -O "$temp_file" "$download_url"
    fi
    
    # Install binary
    local install_path="$INSTALL_DIR/$BINARY_NAME"
    if [ "$platform" = "windows" ]; then
        install_path="$INSTALL_DIR/$BINARY_NAME.exe"
    fi
    
    mv "$temp_file" "$install_path"
    chmod +x "$install_path"
    
    log "Installed to: $install_path"
    
    # Test installation
    if "$install_path" version >/dev/null 2>&1; then
        log "Installation successful!"
        "$install_path" version
    else
        error "Installation failed - binary test failed"
    fi
    
    # Add to PATH instructions
    if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
        warn "Add $INSTALL_DIR to your PATH to use $BINARY_NAME from anywhere:"
        echo "  echo 'export PATH=\"$INSTALL_DIR:\$PATH\"' >> ~/.bashrc"
        echo "  source ~/.bashrc"
    fi
}

# Main installation function
main() {
    log "Installing twat-fs..."
    
    # Check dependencies
    if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
        error "Either curl or wget is required for installation"
    fi
    
    # Get latest release
    local release_info=$(get_latest_release)
    
    # Install binary
    install_binary "$release_info"
    
    log "Installation complete!"
}

# Run main function
main "$@"