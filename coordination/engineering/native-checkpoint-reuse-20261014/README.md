# Native-only checkpoint compatibility

This is a bounded engineering replay of existing accepted inputs. It adds no new map assignments, source claims, or programme registrations. The implementation uses literal native intervals/bounds and existing authenticated custody; it does not invent addition polygons or recompute the full source inventory.

## Actual retained-data result

`actual-native-checkpoint.json.gz` losslessly retains the complete report produced by the reviewed implementation at `3b52c13aaa27403c30a4821c52d3c4fd9121d01c`, comparing baseline `3eaa41fcd21ca07c00d7b13bf3674ce14fae6efe` with candidate `73d26bff6cf5ae195f80bdf3f63927483b6e10bd`. The initial accepted custody is PR #1804 / merge `394b381ff8674926b1b2d15077267668ffa3a4ba`, authenticated through its existing bot receipt, GitHub metadata, and retained original artifact.

- 13,963 source-target native cells across five existing owners; 15,269 cumulative selected cells.
- 1,846 changed native rows: six original-base rows reused, 1,840 acquired through the existing bounded projector.
- Zero lost or reassigned original cells and five actual zero-to-owner visibility witnesses.
- A second transition from the qualified native-only state has zero changed owners/rows and passes unchanged warm reuse.
- Whole read-only run: 63.319 seconds, process peak RSS 593,195,008 bytes. Reader phase/RSS allowance: 1 GiB; Node heap limit: 640 MiB.

This timing includes authenticated artifact acquisition and baseline advancement. It is not a controlled before/after benchmark or a hosted end-to-end queue timing. The actual data replay checks the native qualifier/consumer; fresh derived-archive re-admission is separately exercised by the actual joint/Python producer control below. It does not create new checkpoint acceptance or authorize publication.

## Reproduce

From a checkout containing the immutable commits above, with the normal read-only `gh` authentication available:

```sh
mkdir -p .cache
node --max-old-space-size=640 coordination/engineering/native-checkpoint-reuse-20261014/reproduce.mjs .cache/native-checkpoint-replay.json
```

The output must not already exist. The script consumes the original retained ZIP and Git inputs in place; no raw source copies or whole-source rebuild are needed. Existing checkpoint acquisition validates live acceptance metadata. Missing access/objects or insufficient resource admission fail rather than minting a success result.

## Focused controls

`focused-tests.log` records 102 passing tests, zero skipped, on the implementation commit above:

```sh
node --test --test-concurrency=1 test/selected-checkpoint.test.mjs test/selected-joint-entry.test.mjs test/effective-geographic-regression.test.mjs test/accepted-selected-checkpoint.test.mjs test/accepted-checkpoint-qualification.test.mjs
```

Controls include native-only cold-coordinate bounds, warm joint execution, same-count ownership corruption, malformed native rows/bounds and stale base identity, actual joint/Python retention followed by fresh accepted archive admission, complete source/exception preservation, uncommitted executable drift, and changed scientific `.js` data that cannot use an executable-role exemption. The existing authenticated execution inventories distinguish executable bodies from scientific routes; no filename whitelist or historical hash registration was added.
