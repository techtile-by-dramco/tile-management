#!/usr/bin/env bash
set -euo pipefail

SERVICE_FILE="/home/pi/tile-management/tiles/experiment-launcher.service"
TARGET_LINK="/etc/systemd/system/$(basename "$SERVICE_FILE")"

DEFAULT_CONFIG="/home/pi/tile-management/tiles/experiment-config.yaml"
DEFAULT_WORKDIR="/home/pi/tile-management"

usage() {
    echo "Usage:"
    echo "  $0 install [config_path] [working_directory]"
    echo "  $0 remove"
    exit 1
}

update_service_file() {
    local config_path="$1"
    local working_dir="$2"

    echo "Updating service file with:"
    echo "  CONFIG: $config_path"
    echo "  WORKDIR: $working_dir"

    # Create a temp file
    tmpfile="$(mktemp)"

    # Update ExecStart and WorkingDirectory safely
    sed \
        -e "s|^ExecStart=.*|ExecStart=/usr/bin/python3 /home/pi/tile-management/tiles/experiment-launcher.py $config_path|" \
        -e "s|^WorkingDirectory=.*|WorkingDirectory=$working_dir|" \
        "$SERVICE_FILE" > "$tmpfile"

    # Overwrite original
    mv "$tmpfile" "$SERVICE_FILE"
}

install_link() {
    local config_path="${1:-$DEFAULT_CONFIG}"
    local working_dir="${2:-$DEFAULT_WORKDIR}"

    update_service_file "$config_path" "$working_dir"

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
case "${1:-}" in
    install)
        shift
        install_link "$@"
        ;;
    remove)
        remove_link
        ;;
    *)
        usage
        ;;
esac
