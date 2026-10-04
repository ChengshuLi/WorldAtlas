Actual full CI observations and immutable API/TAP evidence

This packet retains the final complete regression run and the earlier full baseline, each successful with zero skipped tests. Workflow elapsed time uses run_started_at through updated_at after completion and includes startup; it is not summed parallel job time. The final run includes the preceding CI changes and the parity preparation hoist. The separate unchanged-parity run demonstrates substantial runner variation. These are single-run observations, without statistical or isolated hoist attribution.

The original baseline shard-zero log, actual-source preservation controls, and source manifest remain preserved in the prior source packet and are hashed as immutable baseline descriptors here. No new executable, compressed archive, application code, fixture, dataset, workflow, or runner changes are introduced.

Reproduce one run using the retained parser (Python standard library only):

python3 - RUN_API_JSON JOBS_API_JSON SHARD_ZERO_LOG SHARD_ONE_LOG SHARD_TWO_LOG < measurement-parser.txt

Decompress the retained prior baseline shard-zero log into a temporary file for baseline reproduction. The parser extracts successful TAP counts, API job/test-step durations, the actual parity subtests, and run elapsed time; it rejects missing counts, failing/skipped tests, unsuccessful jobs/runs and inverted timestamps. Typed positive and negative control outputs retain known interval checks. The final comparison is in measurement.json, with every interpreted numeric metric bound into the manifest ledger.
