# Official state-source restoration instructions

These state-hosted source bodies were retrieved on 2026-10-05, but their redistribution terms were not established, so the response bodies are not included. The adjacent `.retrieval.json` records preserve the requested URL, retrieval time, HTTP status, exact uncompressed source SHA-256 and response byte count. To restore, retrieve from that URL, verify both `source_sha256` and `source_bytes`, and inspect current reuse terms before redistribution or reliance.

- Georgia Secretary of State County Number List: `georgia-sos-county-roster.retrieval.json`.
- Kentucky Constitution: `kentucky-constitution.retrieval.json`.
- Kentucky Revised Statutes, Chapter 67: `kentucky-revised-statutes-chapter-67.retrieval.json`.

Georgia Constitution, revised July 2025: `https://sos.ga.gov/sites/default/files/forms/Georgia%20Constitution.pdf`. The local fetch returned HTTP 403; the official PDF text interface exposed Article IX for inspection on 2026-10-05. The response bytes and a full-body hash were unavailable. Re-fetch the current official PDF, confirm the July 2025 revision and Article IX, and record its bytes/hash before retaining it. No hash is inferred here.
