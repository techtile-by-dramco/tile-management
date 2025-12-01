#!/usr/bin/env python3
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--message", required=True, help="Message to print")

args = parser.parse_args()

print(args.message)