#!/usr/bin/env python3
"""Produce one complete fresh run under the #1361 owned evidence namespace."""
import argparse
import json
import sys

from packet import ROOT, run_products


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vintage", required=True, help="Fresh name under the declared owned vintages prefix")
    parser.add_argument("--audit-fail-after-compute", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    records = run_products(args.vintage, fail_after_compute=args.audit_fail_after_compute)
    print(json.dumps({"vintage": args.vintage, "outputs": records, "status": "complete"}, sort_keys=True))


if __name__ == "__main__":
    main()
