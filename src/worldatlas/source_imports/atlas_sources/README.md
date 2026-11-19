# Cataloged source files

[`catalog.py`](catalog.py) provides the shared input functions for source imports and map building:

- Read a construction's method and arguments by ID.
- Look up an exact raw source ID and its R2 location.
- `stream_source()` checks the byte length of a complete R2 object and supports cooperative cancellation.
- `download_source()` checks the byte length and SHA-256 before caching a download or reusing a local file. A corrupt cached file raises an error.
- Join ordered, individually cataloged parts into a checked provider file.

A ZIP normally goes into `<work-dir>/<sha256>/source.zip`. Source imports and map building reuse the verified bytes when they use the same work directory. If map building needs the original provider filename, both names can point to the same file on disk through a hard link. Downloads use a temporary file. The final cache path becomes available after verification. Download time excludes verification and processing. Credentials come from the caller.

`test_catalog.py` checks cache reuse, corrupt inputs, timing and multipart files. Source-specific parsing and output persistence belong to the importers.
