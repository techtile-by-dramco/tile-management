#!/usr/bin/env python3
import subprocess
import yaml
import os
import signal
import sys

CONFIG_PATH = "/home/pi/tile-management/tiles/config.yaml"

def main():
    # Load YAML config
    with open(CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)

    script = config.get("script")
    args = config.get("args", [])

    if not script:
        print("ERROR: No script specified in config.yaml")
        sys.exit(1)

    # Build command
    cmd = [script] + args

    # Start the script as a subprocess
    print(f"Launching: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd)

    # Forward SIGTERM (via systemctl stop)
    def handle_sigterm(signum, frame):
        print("Received SIGTERM → stopping child script...")
        proc.terminate()

    signal.signal(signal.SIGTERM, handle_sigterm)

    # Wait for the child script to finish
    proc.wait()
    print(f"Child script exited with code {proc.returncode}")
    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
