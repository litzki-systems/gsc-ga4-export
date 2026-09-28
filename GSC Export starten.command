#!/bin/bash
# Launcher for macOS Finder: resolves its own location, no machine-specific paths.
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON_BIN:-$(command -v python3.12 || command -v python3)}"
if [ -z "$PYTHON" ]; then
  echo "python3 not found. Install Python 3.10+ or set PYTHON_BIN." >&2
  exit 1
fi

# macOS system Python often misses CA certs — point at certifi when available.
if CERT="$("$PYTHON" -c "import certifi; print(certifi.where())" 2>/dev/null)"; then
  export SSL_CERT_FILE="$CERT"
fi

exec "$PYTHON" main.py
