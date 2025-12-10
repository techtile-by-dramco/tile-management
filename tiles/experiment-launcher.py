#!/usr/bin/env python3
import subprocess
import yaml
import os
import signal
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: experiment_launcher.py <config.yaml>")
        sys.exit(1)

    config_path = sys.argv[1]

    if not os.path.isfile(config_path):
        print(f"ERROR: Config file not found: {config_path}")
        sys.exit(1)

    # Load YAML config
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"ERROR: Failed to read YAML: {e}")
        sys.exit(1)

    script_name = config.get("script")
    if not script_name:
        print("ERROR: No 'script' key found in config.")
        sys.exit(1)

    experiment_repo = config.get("experiment_repo")
    script = os.path.join("/home/pi", experiment_repo, "client", script_name)
    args = config.get("args", [])

    # Build command to execute
    # If script is a Python file, run it with python3
    if script.endswith(".py"):
        cmd = ["python3", script] + args
    else:
        cmd = [script] + args

    print(f"Launching: {' '.join(cmd)}")

    # Start the script as a subprocess
    proc = subprocess.Popen(cmd)

    # Forward SIGTERM (systemctl stop)
    def handle_sigterm(signum, frame):
        print("Received SIGTERM → stopping child process...")
        proc.terminate()

    signal.signal(signal.SIGTERM, handle_sigterm)

    # Wait for completion
    proc.wait()
    print(f"Child exit code: {proc.returncode}")

    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
