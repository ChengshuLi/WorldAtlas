# Cataloged source files

[`catalog.py`](catalog.py) provides the shared input functions for source imports
and map building:

- Read an editable construction document by ID.
- Look up an exact raw source ID and its R2 location.
- Stream complete R2 objects with byte-length checks and cooperative cancellation.
- Download or reuse size- and checksum-verified local files.
- Join ordered, individually cataloged parts into a checked provider file.

Cached files live under their content hash in the chosen work directory.
Source imports and map building reuse the same verified bytes. Existing provider
filenames and the generic import filename can share a hard link, avoiding a
second download or a second copy.
Downloads use a temporary file and publish only verified bytes. Download time
excludes verification and processing. Credentials come from the caller.

`test_catalog.py` checks cache reuse, corrupt inputs, timing and multipart files.
Source-specific parsing and output persistence belong to the importers.
