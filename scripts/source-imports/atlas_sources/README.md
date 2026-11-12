# Cataloged source files

[`catalog.py`](catalog.py) provides the shared input functions for source imports
and map building:

- Read a versioned construction document and verify its stored bytes.
- Look up an exact raw source version and its R2 location.
- Download or reuse size- and checksum-verified local files.
- Join ordered, individually cataloged parts into a checked provider file.

Cached files live under their content hash in the chosen work directory.
Downloads use a temporary file and publish only verified bytes. Download time
excludes verification and processing. Credentials come from the caller.

`test_catalog.py` checks cache reuse, corrupt inputs, timing and multipart files.
Source-specific parsing and output persistence belong to the importers.
