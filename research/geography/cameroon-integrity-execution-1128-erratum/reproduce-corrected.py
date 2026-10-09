#!/usr/bin/env python3
"""Safely rerun the exact corrected #1128 producer in a fresh evidence vintage."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from common import run_corrected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("vintage", help="fresh lowercase run name")
    args = parser.parse_args()
    run_corrected(args.vintage)


if __name__ == "__main__":
    main()
