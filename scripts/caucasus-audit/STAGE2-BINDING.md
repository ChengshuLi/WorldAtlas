# Caucasus stage-2 binding

`caucasus_stage2_binding.py` prepares the source-derived seed call and
independently replays the recipe before accepting its gate report. It pins the
recipe, both raw sources and all seven binding/assembler code files. The
validation path passes the independently derived effective snapshot to the
existing strict validator and requires the seed gate's report to match that
derivation and the producer pin exactly.

This helper does not launch a map, select a recipe in Neon, or implement the
stage-2 orchestrator and resume contract. The orchestrator must bind its config,
seed request, gate report and code pins into its identity and invoke the same
independent validation in the core. A bounded Linux test with the real seed and
region pipeline is still required. The existing frozen producer has resource
limits; this helper adds no separate supervisor or memory limit.
