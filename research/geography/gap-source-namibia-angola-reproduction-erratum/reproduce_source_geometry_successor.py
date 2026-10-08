#!/usr/bin/env python3
"""Standalone authenticated reproduction of the 21 x 10 consumed-source matrix."""
import argparse

from authenticated_successors import main


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_name", help="fresh output directory under vintages/")
    main("source-geometry", parser.parse_args().run_name)
