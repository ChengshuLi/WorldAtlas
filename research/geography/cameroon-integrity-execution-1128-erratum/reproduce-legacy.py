#!/usr/bin/env python3
"""Safely replay the exact legacy wrapper and capture its deleted products."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from common import run_legacy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("vintage", help="fresh lowercase run name")
    args = parser.parse_args()
    run_legacy(args.vintage)


if __name__ == "__main__":
    main()
