# Cataloged source files

Resolve and verify the raw files that source imports and map building read from R2.

## Use

Import storage helpers from `worldatlas.source_assets.catalog`. Pass the exact catalog source ID for lookup or the catalog metadata and a local work directory for file acquisition. Credentials come from the caller.

## How it works

- Look up an exact raw source ID and its R2 location.
- `stream_source()` checks the byte length of a complete R2 object and supports cooperative cancellation.
- `download_source()` checks the byte length and SHA-256 before caching a download or reusing a local file. A corrupt cached file raises an error.
- Join ordered, individually cataloged parts into a checked provider file.

A ZIP normally goes into `<work-dir>/<sha256>/source.zip`. Source imports and map building reuse the verified bytes when they use the same work directory. If map building needs the original provider filename, both names can point to the same file on disk through a hard link. Downloads use a temporary file. The final cache path becomes available after verification. Download time excludes verification and processing.

## Code and tests

[`catalog.py`](catalog.py) implements raw-file lookup, verified downloads, caching and multipart assembly. Source-specific parsing and output persistence belong to the importers.

[`r2.py`](r2.py) opens R2 clients and supplies verified local files to the map builder. It can extract individual ZIP members and keep companion files together.

[`test_source_assets.py`](test_source_assets.py) checks cache reuse, corrupt inputs, timing and multipart files.

Run from the repository root with `python .github/scripts/run_tests.py --suite source_assets`.
