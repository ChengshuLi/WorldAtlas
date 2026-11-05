# GeoNames island point extractor

This small standalone research utility reads one reviewed island record from a pinned provider-original country ZIP, checks the exact record, name, country, feature type, and expected point hash, and returns the point. It uses only the Python standard library and bounds archive size. It does not select cells, prove offshore-islet membership, publish a map, or replace a source archive. Run `python -m unittest -q test_geonames_extract` in this directory for the synthetic tests.
