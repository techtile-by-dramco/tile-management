#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="experiment-launcher.service"
SERVICE_FILE="/home/pi/tile-management/tiles/$SERVICE_NAME"
TARGET_LINK="/etc/systemd/system/$SERVICE_NAME"

DEFAULT_CONFIG="/home/pi/tile-management/tiles/experiment-config.yaml"
DEFAULT_WORKDIR="/home/pi/tile-management"

usage() {
    echo "Usage:"
    echo "  $0 install [config_path] [working_directory]"
    echo "  $0 remove"
    exit 1
}

create_working_dir() {
    local working_dir="$1"

    # Check if the directory exists
    if [ ! -d "$working_dir" ]; then
        echo "Directory $working_dir does not exist. Creating..."
        mkdir -p "$working_dir"
        if [ $? -eq 0 ]; then
            echo "Directory created successfully."
        else
            echo "Failed to create directory $working_dir" >&2
            exit 1
        fi
    else
        echo "Directory $working_dir already exists."
    fi
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

    create_working_dir "$working_dir"

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
    sleep 1
}

remove_link() {
    echo "Removing systemd service link..."
    
    if [ -L "$TARGET_LINK" ]; then
        echo "Stopping systemd service ..."
        systemctl stop "$SERVICE_NAME"

        rm "$TARGET_LINK"
        echo "Removed symlink: $TARGET_LINK"
    else
        echo "No symlink found at $TARGET_LINK"
    fi

    echo "Reloading systemd..."
    systemctl daemon-reload
    echo "OK"
    sleep 1
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
