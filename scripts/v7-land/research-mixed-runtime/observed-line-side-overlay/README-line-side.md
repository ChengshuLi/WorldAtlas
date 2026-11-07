# Source-observation line-side research overlay

This code-only overlay adds a named-point component selector that reads a
source-linked, versioned multiline observation from a Neon decision export.
It checks a point against a visible line segment, never interpolates across a
gap, rejects ambiguous segment endpoints and antimeridian signs, and requires a
human-selected WGS84 same-latitude separation screen. This separation is not
the shortest distance to the polyline and is not a confidence or accuracy
estimate. Human review must establish the source convention and component
identity; independent full-component checks are required before selection.

Apply this overlay to the reviewed source-negative mixed runtime and point
runtime, preserving the existing airport, large-archive, multipolygon, and
source-negative changes. The exporter expects the project observation table.
The line source, geometry, review decisions, input requests, and result data are
not included; those belong in the project's database and source storage.

Run synthetic point, claim-validator, and mixed-runtime suites against the
assembled runtime. The line-side helper requires `pyproj` and uses WGS84
geodesics. No existing decision is changed merely by publishing this overlay.
