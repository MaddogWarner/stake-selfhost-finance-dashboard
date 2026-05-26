#!/usr/bin/env bash
# Usage: ./scripts/rotate-token.sh <new-session-token>
#
# Updates STAKE_SESSION_TOKEN in .env and comments out STAKE_USERNAME / STAKE_PASSWORD.
# Run this after copying a new token from the backend logs or your browser cookies.
set -euo pipefail

TOKEN="${1:?Usage: rotate-token.sh <session-token>}"
ENV_FILE="$(dirname "$0")/../.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Error: .env not found at $ENV_FILE"
  exit 1
fi

# Set or replace STAKE_SESSION_TOKEN
if grep -q "^STAKE_SESSION_TOKEN=" "$ENV_FILE"; then
  sed -i '' "s|^STAKE_SESSION_TOKEN=.*|STAKE_SESSION_TOKEN=${TOKEN}|" "$ENV_FILE"
else
  echo "STAKE_SESSION_TOKEN=${TOKEN}" >> "$ENV_FILE"
fi

# Comment out username/password if they are set (not already commented)
sed -i '' "s|^STAKE_USERNAME=|# STAKE_USERNAME=|" "$ENV_FILE"
sed -i '' "s|^STAKE_PASSWORD=|# STAKE_PASSWORD=|" "$ENV_FILE"

echo "Done. STAKE_SESSION_TOKEN updated in .env; STAKE_USERNAME/STAKE_PASSWORD commented out."
