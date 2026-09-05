#!/usr/bin/env bash
# setup.sh - install Termux packages and Python requirements for AniNow
# Run this in Termux from the repository root: ./setup.sh

set -euo pipefail

REQ_FILE="$(pwd)/requirements.txt"

cat <<'EOF'
This installer will run the following actions (Termux):
  - pkg update && pkg upgrade -y
  - pkg install -y python mpv git
  - pip install --upgrade pip
  - pip install -r requirements.txt

It requires network access and will modify your system packages. You can cancel at the prompt.
EOF

read -p "Proceed with installation? [Y/n]: " ans
ans="${ans:-Y}"
if [[ ! "$ans" =~ ^[Yy] ]]; then
  echo "Cancelled. You can still manually run the commands listed in the README."
  exit 1
fi

echo "Updating Termux packages..."
pkg update -y && pkg upgrade -y

echo "Installing system packages: python mpv git..."
pkg install -y python mpv git

# Ensure pip exists
if ! command -v pip >/dev/null 2>&1; then
  echo "pip not found; attempting to install pip via python -m ensurepip"
  python -m ensurepip --upgrade || true
fi

echo "Upgrading pip and installing Python requirements..."
python -m pip install --upgrade pip
if [ -f "$REQ_FILE" ]; then
  python -m pip install -r "$REQ_FILE"
else
  echo "requirements.txt not found; skipping pip installs."
fi

echo "Installation complete. You may want to run './install.sh' to create the AniNow command in ~/bin and ensure ~/bin is in your PATH."
