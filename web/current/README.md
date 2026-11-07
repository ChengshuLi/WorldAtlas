# Current map UI

This folder contains the streamlined WorldAtlas interface deployed at the Cloudflare root. It renders a single native grid; the prior V7 review remains available at its existing versioned URL. `config.json` pins the row-offset and run streams, which remain in R2. The map data are an existing research composition with the Iceland-boundary update, not the requested fresh end-to-end rerun; some previous water classifications were reused and not revalidated.

The displayed combined SHA-256 is calculated over the decompressed little-endian u32 row-offset bytes followed immediately by the decompressed little-endian u32 run bytes. It identifies these two streams, not source data, metadata, code or the interface. The client separately verifies the row and run hashes before use. The checked-in category counts were independently computed from the complete grid.

The original OpenStreetMap attribution remains visible in the header and links to its licence; the linked source page includes the SeaVoX v19 attribution and licence. The linked source page identifies known current inputs and states its specific inventory gaps. It does not claim a complete source or geographic-decision history. The deployment uses an immutable `review/worldatlas-current-20261107-v2/` asset prefix, while the Worker serves the root HTML from `review/index.html`. Earlier V2/V4/V5/V6/V7 query URLs continue to route to their original versioned pages.

Run `node --test tests/current-map.test.mjs` for lightweight DOM-model interaction and configuration tests. These tests do not replace a real-browser rendering check.
