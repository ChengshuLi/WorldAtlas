# Fresh stage-2 geodesic prototype

Research prototype. It produces no map unless the source-producer freeze and
selected Neon land-policy crosswalk are both explicitly enabled after review.
The terminal-aware seed-producer freeze was independently reviewed, but its
route and citation schema predates the final Neon export; its gate is closed. The selected-policy crosswalk is a provisional prototype awaiting real Neon
schema alignment and independent review; its gate remains closed. Existing inputs and historical checkpoints
are not accepted as seeds, hints or assignments.

The intended sequence, in one guarded process group, is:

1. Verify pinned stage-1 mask/component provenance and independently re-resolve
   source-backed selected witnesses on those current streams.
2. Run the reviewed seed producer on the selected Neon mainland rules and
   boundaries. Validate geographic closure and physical/component coverage.
3. Generate seed tiles and representatives. Verify every tile against the seed
   with an independent compiled verifier and check representative membership.
4. Generate source-only hints. Certify the candidate or run the exact WGS84
   search for every non-seed physical component; hints never become labels
   without one of those checks.
5. Write the research output atomically and let the guardian/monitor write its
   acceptance marker last. Water assignment and List 1 overrides are excluded.

Fresh artifact paths, requests, source code and hashes are bound to the work
identity. Resume requires a complete derived manifest, matching paths and pins,
matching code and policy, and a valid core checkpoint if core work has started.
Incomplete or uncertain state must be inspected before retrying. This identity
is an integrity/provenance aid, not cryptographic authentication of Neon itself.

The monitor samples memory and cannot guarantee detection of transient spikes;
processes that escape its group and simultaneous guardian/monitor failure are
outside its containment. Independent review of source evidence, boundary
semantics, numerical bounds and the selected policy is still required. The
physical mask differences relative to V7 are not island overrides.

Run synthetic tests with:

    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -m unittest discover -q

Do not run production or publish the prototype based on these tests. The
terminal-aware closure integration and selected-policy crosswalk must be
independently reviewed against real selected Neon data before enabling the build.
