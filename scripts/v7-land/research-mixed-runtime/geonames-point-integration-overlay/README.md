# GeoNames source-point integration

This research overlay connects the bounded GeoNames country-archive extractor to the point adapter, resolver, claim validator and mixed runtime. It verifies source SHA, unique island record, exact point, region-label containment and current physical component. A point does not establish an island's entire physical extent or nearby islets. These files have passed synthetic integration tests and a separate provider-source preview; no global map has used this integration yet.

Use the separately preserved no-host-floor mixed runtime and OSM map-export overlay as the base. Copy their directories to the names shown here and replace the matching files. Copy the existing point and identity modules as siblings before overlaying the point files, and place the claim validator in its sibling directory. Recheck all code and input pins before running. No source geographic records, decisions, credentials, or result grids are included.
