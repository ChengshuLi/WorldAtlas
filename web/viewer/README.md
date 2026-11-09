# Map viewer

This folder contains the streamlined WorldAtlas interface deployed at the Cloudflare root. It renders the V8.0 native grid. `config.json` pins the row-offset and run streams, which remain in R2. The V8.0 reproduction matched the published grid byte for byte.

The displayed combined SHA-256 is calculated over the decompressed little-endian u32 row-offset bytes followed immediately by the decompressed little-endian u32 run bytes. It identifies these two streams, not source data, metadata, code or the interface. The client separately verifies the row and run hashes before use. The checked-in category counts were independently computed from the complete grid.

OpenStreetMap and SeaVoX attributions are available through Data sources. OpenStreetMap Foundation guidance recommends presenting its attribution on startup or beside a browsable map; this interface follows the requested source-page-only presentation. The linked source page lists the main current inputs. The deployment uses an immutable `review/worldatlas-current-20261107-clean-v1/` asset prefix, while the Worker serves the root HTML from `review/index.html`. The Worker maps `/v8.0/sources` and `/v8.0/sources.html` to the existing public `/review/v8.0/sources.html` object.

Use the [release workflow](../../scripts/map-build/pipeline/README.md#stage-review-and-publish-a-release)
to package the browser modules with a completed build. The candidate bundle
contains the viewer’s release-specific configuration and base URL.

Run `node --test web/tests/current-map.test.mjs` for lightweight DOM-model interaction and configuration tests. These tests do not replace a real-browser rendering check.
