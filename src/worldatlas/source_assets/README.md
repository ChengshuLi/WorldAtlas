# Cataloged source files

Neon records the R2 location, byte size, and SHA-256 of each raw source. The shared local cache gives source imports and map builds a verified file to read.

## Use

Use `catalog_sources(database, source_ids)` to look up raw files by ID. Create a `SourceCache(input_directory)` and pass each returned file pin to `acquire()`. Use `assemble()` when a provider file is stored as ordered parts. Call `close()` after acquiring the files to close the cache's R2 client. A map build gets its pins from the saved input selection.

## How it works

Whole files are kept at `inputs/<sha256>/<filename>`. A new cache instance checks the size and SHA-256 before reusing a file. Within that instance, it remembers verified paths. ZIP members retain their relative paths so GDAL can find files that belong together. Downloads and extractions become visible at their final paths after verification. Failed transfers leave no completed cache file.

Source imports and the map builder use the same disk cache when the import's `--work-dir` is the build workspace's `inputs/` directory. This includes the inland-water files, so a new physical build can reuse them without downloading them again.

## Code and tests

| File | Responsibility |
| --- | --- |
| [`catalog.py`](catalog.py) | Read raw file pins from Neon in one query. |
| [`cache.py`](cache.py) | Cache verified objects, ZIP members, and multipart files. |
| [`shared/database.py`](../shared/database.py) | Open Neon connections. Callers own their queries and transactions. |
| [`shared/r2.py`](../shared/r2.py) | Open the R2 client and read or write objects. The project endpoint is shared by imports, builds, and releases. |

Run from the repository root with `python .github/scripts/run_tests.py --suite source_assets`. The tests check reuse, failed transfers, checksums, and multipart assembly.
