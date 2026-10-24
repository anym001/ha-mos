# shellcheck shell=bash
# Installs the card's own npm project in frontend/ next to the root tooling.
if command -v npm >/dev/null 2>&1; then
    log_header "Installing the card's Node.js dependencies"
    (cd frontend && npm ci --silent)
fi
