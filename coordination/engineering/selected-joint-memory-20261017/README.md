# Bounded selected-native comparison

Hosted run [39005089661](https://github.com/ChengshuLi/WorldAtlas/actions/runs/39005089661) completed baseline and candidate qualification, then Node exhausted its default heap at approximately 4,088 MB before native comparison completed. No geography receipt was emitted and no merge occurred.

The native consumer previously expanded every changed base row, then deep-copied all base intervals twice into complete before/after projections. The retained eight-package comparison contains 20,514,842 original base runs across 107,587 changed rows. This fix visits 128-row batches through the existing authenticated projector. Existing qualified cached rows remain intact; newly expanded rows and visit-local decoded-container reuse are discarded in `finally`. Every whole encoded/decoded hash, complete row/domain/owner check and genuine transition boundary remains in effect. Both cumulative patches are validated completely before scope selection. Conservation checks still traverse every changed row. Visibility uses a second bounded pass so its latitude acquisition does not change the original comparison custody snapshot.

## Executed evidence

`actual-native-comparison.json` records one retained-data arithmetic reproduction on Node 24.19.0 under its default heap. Original native base manifest SHA-256 was d9954fa51d18e4ce785679f920e4b6ac1ebd3cf07ce03fa7e7e674cb2a42faba; the retained emitted loader checked every encoded/decoded native body. Exact baseline/candidate cumulative patches were read from the selected sidecar pins:

- Baseline 3b3e9e675cfb37999d5665438f9fbf25bbd4238b: c8a5133bc78923b8ca78c6feeb992b87ceaa8c17:coordination/engineering/greenland-repair-delivery-20261017/composition-current-001/patch.json, SHA-256 bb62deda4e1bf4b2d51a08baf6503b21ed13e54a9f1cf03e7c52e408b3518643
- Candidate 0db52cf5a1b7c06a1b27989ec044face48c65286: f6f6f15109d63b918e1a4569ac68906e948117a7:coordination/engineering/five-repair-delivery-20261017/composition-004/patch.json, SHA-256 c3c83e3bec5a1dbe60df63eea7d22d5173281de1ad1068c5632cbda674c6cf9d

The bounded 256-row old eager versus new batched arithmetic had identical complete before/after row hashes. The complete batched arithmetic checked every changed row, found zero lost/reassigned cells, and peaked at 1,100,084 KiB RSS. This is arithmetic evidence, not a repeated source qualification, full private-transition memory measurement, visibility census, or hosted acceptance receipt. The old eager whole-data path was not rerun after the actual hosted OOM.

Focused genuine-state tests separately exercise private transition admission, zero rows without extra reads, exact projector custody, old API compatibility, transient-row cleanup on failure, and exact eager-versus-batched visibility witnesses for an appended native authority. The fixture now supplies compressed normative latitudes with both encoded and decoded pins so the genuine visibility path runs.

No scientific rule, native assignment, source approval, emitted map, default heap setting or acceptance criterion changes. The reviewed checker must still pass the real hosted map delivery before acceptance.
