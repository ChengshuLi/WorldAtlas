# Iceland ocean boundary source extraction

From the repository root, run

    python scripts/raw-to-structured/iceland/extract_s130_iceland.py --archive S-130.zip --output iceland-routes.json

Use the archive registered as `iho-s130-global-sea-areas`, version
`1.0.0-44997a24a4fe`. The extractor verifies the ZIP and GML hashes and
recovers the two Iceland rhumb routes and their four endpoint coordinates.
It reads the endpoints of construction lines `M.1505` and `M.1504`, then
reverses their order to match the selected routes in Neon. For Jan Mayen
South Cape, the line endpoint is `-9.04279190236343` longitude and the
associated point is `-9.04279190236342`. The selected Neon record uses
the line endpoint. The extractor was reconstructed from the retained
source and records. It emits a new JSON document.
