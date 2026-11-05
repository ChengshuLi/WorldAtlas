# Shared GeoNames ZIP extraction research overlay

This non-standalone research overlay groups point decisions by exact source
identity and country, then reads each GeoNames ZIP once per group. The extractor
retains individual name, record, country, coordinate and geometry-hash checks;
source and code files are rehashed after resolution. It does not select a new
geography or update the active runtime merely by being stored here.

The two runtime files are a reviewed research freeze, not a direct-run or
production configuration. Other modules and an original resolver must be
assembled from matching reviewed versions to run the integration parity test.
The synthetic extractor tests can run from this directory. The tests in this
package contain fictional records, not source or map data.

Before activation, compare the next necessary bounded real-selected-decision
replay against the pinned original, including status, revision, counts, all
ordered claims and semantic source/input metadata. Exclude only intentionally
changed code hashes and volatile telemetry. Review the direct-run invocation
against the current no-artificial-process-memory-cap instruction. No map build,
full-source parity result, deployment or production authentication is claimed.

The batch extractor rejects repeated requested record IDs within one
source/country group before component resolution. The original resolver can
reject their shared component later, so invalid-input failure timing or message
may differ. Review inherited source-size bounds and direct-run behavior before
activation; no artificial process-memory cap is introduced by this package.
