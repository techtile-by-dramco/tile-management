#!/usr/bin/env bash
set -euo pipefail

SERVICE_FILE="/home/pi/tile-management/tiles/experiment-launcher.service"
TARGET_LINK="/etc/systemd/system/$(basename "$SERVICE_FILE")"

usage() {
    echo "Usage: $0 {install|remove}"
    exit 1
}

install_link() {
    echo "Installing systemd service link..."

    if [ ! -f "$SERVICE_FILE" ]; then
        echo "ERROR: Service file not found: $SERVICE_FILE"
        exit 1
    fi

    if [ -L "$TARGET_LINK" ]; then
        echo "Symlink already exists: $TARGET_LINK"
    elif [ -e "$TARGET_LINK" ]; then
        echo "ERROR: A file already exists at $TARGET_LINK (not a symlink)"
        exit 1
    else
        ln -s "$SERVICE_FILE" "$TARGET_LINK"
        echo "Created symlink: $TARGET_LINK -> $SERVICE_FILE"
    fi

    echo "Reloading systemd..."
    systemctl daemon-reload
    echo "OK"
}

remove_link() {
    echo "Removing systemd service link..."

    if [ -L "$TARGET_LINK" ]; then
        rm "$TARGET_LINK"
        echo "Removed symlink: $TARGET_LINK"
    else
        echo "No symlink found at $TARGET_LINK"
    fi

    echo "Reloading systemd..."
    systemctl daemon-reload
    echo "OK"
}

# --- MAIN LOGIC ---
if [ $# -ne 1 ]; then
    usage
fi

case "$1" in
    install)
        install_link
        ;;
    remove)
        remove_link
        ;;
    *)
        usage
        ;;
esac
