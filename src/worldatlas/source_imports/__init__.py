"""Construct editable geography from cataloged raw sources.

``run_import`` runs stored constructions and ``contracts`` generates their
database checks. ``worldatlas.source_assets`` resolves and caches raw inputs.
``features``, ``iho``, ``osm``, ``traces``, and ``watersheds`` produce
geometry using WGS84 line sampling from ``worldatlas.geodesy`` where needed.
"""
