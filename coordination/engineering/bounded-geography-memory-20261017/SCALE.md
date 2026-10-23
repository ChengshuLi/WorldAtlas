# Native checker scale probes

Put these three small scripts in the same engineering packet directory (three levels below the repository root). They import the committed actual consumers and test/fixtures/native-word-store.mjs. No scientific producer or geographic approval is involved. Run each size in a fresh process; retain its small JSON output, not generated native bodies.

```
for words in 262144 1048576 4194304 16777216; do
  node --expose-gc coordination/engineering/bounded-geography-memory-20261017/scale-native-words.mjs window "$words"
done
SCALE_PATTERN=dispersed node --expose-gc coordination/engineering/bounded-geography-memory-20261017/scale-native-words.mjs window 4194304
node --expose-gc coordination/engineering/bounded-geography-memory-20261017/scale-native-words.mjs whole-buffer-kernel 16777216
for intervals in 4096 65536 1048576 4194304; do
  node --expose-gc coordination/engineering/bounded-geography-memory-20261017/scale-native-intervals.mjs "$intervals"
done
for components in 256 1024 4096 16384; do
  node --expose-gc coordination/engineering/bounded-geography-memory-20261017/scale-native-components.mjs "$components" native
done
node --expose-gc coordination/engineering/bounded-geography-memory-20261017/scale-native-components.mjs 8193 polygon
```

No heap is raised. `--expose-gc` permits a comparable fixture-generation/consumer boundary; maximum RSS still covers the entire child lifetime including fixture creation. Default scratch is the current working directory. Set SCALE_SCRATCH_PARENT only to an owned location whose actual filesystem backing and free space have been checked. On tmpfs, spool bytes consume memory outside process RSS; on a disk filesystem, page cache is still a reclaimable memory term. The harness reports scratch bytes and cleanup separately. The whole-buffer kernel uses the unchanged production codec and reproduces the old encoded/raw/unshuffled/canonical allocation sequence; it is not a whole-checker benchmark.

The mathematical source is generated in fixed windows; a complete canonical digest and every returned word are checked without retaining the whole expected array. Dense-row probes consume every interval and check exact ordered loss output. Component probes deliberately hold the actual input and complete witness output so the separate O(component count) term remains visible.

Small deterministic CI controls are test/native-word-store.test.mjs, test/native-stream-custody.test.mjs, test/native-interval-stream.test.mjs and test/native-interval-projection.test.mjs. They cover failures and cleanup as well as equality. Native storage/window results do not establish constant total checker memory: parsed ledgers, authority/patch graphs, largest original geometry, metadata and complete report output remain disclosed terms.
