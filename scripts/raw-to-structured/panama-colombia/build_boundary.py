#!/usr/bin/env python3
"""Download the Panama–Colombia OSM source and save its boundary in Neon."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.osm_boundary import run_cli


SOURCE_ID = 'osm-panama-current-way-full-bundle'
BOUNDARY_ID = 'panama_colombia_osm_admin_boundary'
RATIONALE = ('Reconstruct the administrative boundary from the archived OSM way '
             'membership and selected node coordinates.')


if __name__ == '__main__':
    run_cli(SOURCE_ID, BOUNDARY_ID, RATIONALE)
