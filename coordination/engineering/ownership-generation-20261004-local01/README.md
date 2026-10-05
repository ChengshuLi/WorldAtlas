Ownership cache generation fix for issue #849

A geography load replaces the ownership-runtime index and bucket cache. Calls capture the generation map before waiting for the index; failures only clear their own pending request. Nearby-year reads reuse their index and bucket, retaining the two-bucket bound.

Regression controls retain stable location/owner identities, exact supported interval and source record provenance. The unmodified baseline fails same-path reload by reading its index only once across two generations. Tests cover late index and bucket rejection after a new successful generation. These are code controls, not live deployment or performance acceptance. No database, geometry, ownership assets or factual records change.

Run: `node --test --test-timeout=30000 test/compact-map-client.test.mjs`.
