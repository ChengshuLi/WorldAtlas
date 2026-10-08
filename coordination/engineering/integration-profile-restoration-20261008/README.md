# Integration profile restoration boundary

At base 689fa0618ce61827adc8862c3e065bcfcf97417b, worker 37834613015 failed before evidence tests because the deliberately sparse evidence checkout lacks the canonical product namespace. The runner now invokes the unchanged canonical preparation only for `full`. All selection, native input, browser and zero-skip checks remain unchanged.

Source freeze 34bd326b3710a1f40d9d9348532d752b0c5b1a4a was executed twice in fresh copies of the exact workflow evidence inputs: both real entries passed 207 tests with zero skips and no canonical namespace. Every one of the 710 ordinary source bodies was checked before and after both runs. The complete gzip JSON source image retains each original path, mode, Git OID and body. Logs differ in real execution timing.

Six real-entry boundary controls cover absent evidence helper, full restoration before a reader, missing/failing full helper rejection, invalid profile and skip rejection. Full positive controls use a controlled tiny helper; they do not qualify world restoration. Existing full normal CI must qualify the real full profile.

Commands: `INTEGRATION_PROFILE=evidence INTEGRATION_SHARD=0 node scripts/run-integration-tests.mjs` in each restored sparse image; `node --test --test-reporter=tap test/integration-profile-restoration.test.mjs` for boundary controls. Runtime: Node 24.19.0. The retained preparation-helper text records the actual local metadata/source-custody invocation, including original absolute paths; it is not an additional scientific algorithm or a portable replacement for the normal entry.

The packet records complete encoded/decoded source-image pins; the preparation operating estimate separately charges the whole installed Node executable and retained output allowance. No geometry, native scientific products, workflows or evidence policies changed. Initial inherited NODE_TEST_CONTEXT fixture failure is retained honestly in report.json; only the fixture environment was corrected to emulate a plain CLI.
