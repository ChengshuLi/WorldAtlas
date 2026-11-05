# Historical stage2 closure code

This isolated historical overlay preserves three exact code blobs authenticated by the draft153 stage2 orchestration closure. The fresh stage2 orchestrator invokes the mainland witness resolver and hint watchdog; the latter invokes the hint diagnostic. The rest of the pinned runtime, inputs, source receipts and dependencies must be separately assembled and authenticated. These files are not a complete runnable release, a map publication, or evidence of source correctness.

The historical hint helper, preserved elsewhere, uses spherical-nearest sampling as an internal heuristic and does not certify a geodesic nearest witness; final selected land distances in that historical method use WGS84. These historical bytes are preserved for audit and reproduction only, not as approval for a new distance method or a claim that the heuristic reproduces any other implementation. Use the currently approved geodesic method for new work.

The included tests use synthetic fixtures; the mainland test was adapted for the historical resolver's required continent-level entity field. In a separately assembled matching runtime, `test_cli`, `test_watchdog`, and `test_hints` exercise the hint path; `test_resolve_mainland` exercises the mainland resolver. No raw sources, decisions or maps are included.
