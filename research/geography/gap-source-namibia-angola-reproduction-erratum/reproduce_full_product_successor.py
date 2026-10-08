#!/usr/bin/env python3
"""Standalone authenticated scan of all 21 candidates x 270 full-product rows."""
import argparse

from authenticated_successors import main


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_name", help="fresh output directory under vintages/")
    main("full-product", parser.parse_args().run_name)
