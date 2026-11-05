# Caucasus stage-2 binding

`caucasus_stage2_binding.py` prepares the source-derived seed call and
independently replays the recipe before accepting its gate report. It pins the
recipe, both raw sources and all seven binding/assembler code files. The
validation path passes the independently derived effective snapshot to the
existing strict validator and requires the seed gate's report to match that
derivation and the producer pin exactly.

The stage-2 orchestrator optionally invokes this helper when configured with the
source pins, and binds its config, seed request and gate report into the derived
manifest and resume identity. The core independently replays and validates the
same derivation. The option rejects pre-existing seed handoffs. A bounded Linux
test with the real seed and region pipeline is still required, and the selected
Neon recipe is not yet present. The existing frozen runtime still has resource
limits; the separate direct-run refactor must remove them. This change adds no
supervisor or memory limit and does not launch a map.

The direct gate now requires `worldatlas-stage2-seed-direct-request-v2` with exactly the positive integer `strip_rows` control and calls `run(request, work, output)`. The currently frozen outer orchestrator still produces the older request; it must be adapted to the independently reviewed v2 producer and closure contract before this optional path can run. The candidate producer and checker allowlists have not been promoted, and a real-GDAL closure test remains outstanding.
