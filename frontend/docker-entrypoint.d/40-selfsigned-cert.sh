#!/bin/sh
set -eu
CERT_DIR=/etc/nginx/certs
if [ ! -f "$CERT_DIR/server.crt" ] || [ ! -f "$CERT_DIR/server.key" ]; then
    mkdir -p "$CERT_DIR"
    echo "Generating self-signed TLS certificate (first run)..."
    openssl req -x509 -newkey rsa:2048 -nodes -days 825 \
        -keyout "$CERT_DIR/server.key" -out "$CERT_DIR/server.crt" \
        -subj "/CN=stake-dashboard" \
        -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
    chmod 600 "$CERT_DIR/server.key"
fi
