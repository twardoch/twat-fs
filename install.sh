#!/usr/bin/env bash
# install.sh — Install twat-fs locally
# File system utilities for twat with support for multiple upload providers
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Installing twat-fs..."
uv pip install -e . 2>/dev/null || pip install -e .
echo "Done."
