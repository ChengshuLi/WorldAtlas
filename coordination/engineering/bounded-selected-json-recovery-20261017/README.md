# Bounded selected JSON integration (work in progress)

The exact six-file parser donor is 7bd9f145923826df056b4e4cb29ca5fc5a58a8f2, recovered in f0072ee0. This integration reuses that parser and its authenticated disk store for selected cumulative patches and ledger native rows. The same native validator and canonical hash logic consume repeatable browser-safe sequences. No Node storage code enters package `src`.

The stream producer lifecycle fix was contributed by the CI recovery worker and independently reviewed by the coordinating root. Donor v2 SHA-256: 8fee61131fa80308e4e850fa6433674495b1c9dfd28505d06056cb515552ff70. The contributor reproduced the original intermittent abort on repetition 7, supplied a deterministic negative control, and ran 40 fixed process suites (360 assertions); the added late physical failure control also passes. Local integrated tests preserve full EOF authentication and join producer cleanup after early consumer exit.

Evidence so far: original donor 19/19; native canonical/consumer 32/32; sequence 4/4 including 500,000 intervals under a 48 MiB V8 heap; execution-byte mutation refusal 4/4. Combined checkpoint suite initially 121/128, with the seven remaining failures identified as duplicate test cleanup hooks and corrected separately. Final full integrated evidence remains required. A selected compressed-ledger control checks malformed late JSON, wrong decoded hash, exact accepted values, unchanged baseline, producer cleanup and scratch release.

This is a recoverable implementation checkpoint, not completion of issue 2396. Component metadata and geometry, root scope/source envelopes, and appended source-proof bodies still require measured retention boundaries. Input streaming does not imply constant total memory; largest component/scalar and requested output size must be reported separately. Genuine package build, browser closure, geography and expanded consumer controls remain mandatory.

## Component and accepted-envelope continuation

The browser-safe sequence implementation now resides in existing standalone `src/native-grid.js`; the separate helper module is deleted. This avoids adding a dependency to historical native preparation/runtime closures. The same store now exposes ordinal component lookup and disk-backed root metadata vectors, and its existing row parser admits nested current-rebind native rows. Accepted original patch products are streamed too. Normalized and candidate component indexes perform ordered on-demand lookup instead of retaining geometry values; accepted native/target operands use immutable cursor sources plus only newly projected values. Visibility batches retain at most 16 current candidate components, while the required witness output remains explicit.

Additional evidence: unified parser/sequence 25/25; native preparation and differential scanner 26/26 (plain launch with inherited NODE_PATH removed, no guard weakening); authentic joint producer/Python retention/archive 2/2; new envelope controls 4/4. The envelope stress consumes 10,000 ordered 8 KiB metadata objects, over 80 MB of JSON under a 48 MiB V8 heap, checking the complete canonical hash, each ordered value and scratch cleanup. The combined checkpoint/canonical/consumer run passed 145/151 initially; all six remaining failures were view-shape or obsolete transport-batch expectations, updated to compare exact materialized values and explicit full-stream custody, then passed individually (1+5). A final fresh combined run remains required.

Remaining limits are explicit: an individual component geometry/scalar is framed as one JSON value; registry/root object metadata not represented as a vector can still grow; fresh authority/source qualification and the legacy rebind recomputation still contain eager scientific graphs. The fixed-heap envelope test is parser/retention evidence, not proof of a bounded full scientific route. No completion claim is made for issue 2396. Immutable same-scientific-input full-route measurements must be repeated on this checkpoint.

## Immutable 886a validation and measured optimization

The frozen 886a6e7f checkpoint/joint/canonical/envelope run passed 173/173. Independent review passed 696/697 in 29 suites plus envelope 4/4; the sole remaining failure was the obsolete unchanged-production-text assertion. The accepted 07d177c eager numerical preimage is now retained byte-for-byte in a test fixture, with both whole-file and original-body SHA-256 pins. A reviewer-contributed deterministic matrix makes 8,048 output/error comparisons, including 4,004 exact refusal-message comparisons, against arrays and cursors. This does not replace executable-byte authentication.

On identical 100k-interval scientific inputs, independent 886a measurements reported median RSS 173.8 -> 106.9 MiB, wall time 1.23 -> 2.69 s, 4.80 MB spill and no surviving scratch descriptors. Exact science, witnesses and scopes matched. The memory/time tradeoff is explicit. CPU profiling identified canonical traversal and framing as larger than disk-iterator cost. The next change specializes finite numeric triples in the existing canonical hasher and reuses the same store's existing row serializer for nested envelope rows. Signed-zero, exponent/subnormal formatting, sparse arrays, malformed values, duplicate keys and complete hashes remain controlled; no retained-value cache was added. New canonical/envelope/eager controls pass 14/14. Fresh same-input performance measurements remain required.


## Continuing completed-authority collection boundary

The successor starts from accepted `282d14b4682f738fed6a0e6f3ee0d0e4b775d611` and integrates exact frozen `a34b867ed48b8f324856fae4763f31afde194284`. Independent a34b review is retained at [#2396 comment 6241225256](https://github.com/ChengshuLi/WorldAtlas/issues/2396#issuecomment-6241225256); it does not review successor edits.

Completed-constructor append admission now authenticates constructor, evidence and candidate bodies through the same existing store, with `ledger_rows` selecting its existing component parser. Registry preimage acquisition is shared with the synchronous authority entry. Both adapters call the same completed scientific verifier. The verifier retains target ordinals rather than geometry-valued Maps, and uses one interval merge implementation for literal output and stored sequences. Appended component joins retain ordinals rather than original geometry graphs. The literal merge preimage is preserved with a complete-file hash and 1,000 deterministic value/refusal comparisons. No new parser, cache or validator is introduced.

Observed local checks before the successor freeze: 134 parser/source/checkpoint controls passed; six sequence controls passed including the merge preimage matrix; six additional genuine completed/non-completed transition and coherently repinned constructor refusal controls passed; 36 adjacent native-authority, source-delivery, native-consumer and joint-check controls passed. The fixture constructs completed output from its actual qualified original source proof and exposes `nativePatchRows` for genuine density measurements. Final review and new full-route measurements remain required.

Remaining memory terms are explicit: ID/ordinal indexes grow with source/component count, active merge cursors grow with patch count, and one component or metadata-vector element can still be large. Non-completed fresh source-family acquisition and legacy rebind graphs remain open. Required output arrays of literal producer APIs remain output-size terms. The earlier a34b 100k same-input benchmark observed approximately 39% RSS reduction with 1.60x wall time; local raw artifacts were lost in an executor reset, so that historical observation is not a new successor measurement. Full local package build remains unexecuted; actual hosted package/build gates are required.

Independent review of `12bd3201063a3b6255c7c5b8ec401d4c566e9960` found that merge cursor initialization preceded cleanup coverage. The original negative control reproduces an `initial read sentinel` with one producer still active. The successor correction acquires and advances each cursor inside cleanup coverage, attempts every close, and preserves the primary producer error over a secondary cleanup failure. Eight sequence tests now pass, including row/interval first-read and midstream failures and normal/throwing early returns; the six genuine completed-entry controls pass again. Finding attribution: independent CI reviewer; implementation and tests: this author. The original 12bd checkpoint is superseded, not silently treated as passing this invariant.

Fixture-only growth support now snapshots `sourceFeatures` and regenerates the actual source collection, owner roster, complete coordinate certificate/facts, membership/source inventories and physical/measured target records. `targetOwners` constructs and qualifies genuine multi-owner native authority output rather than duplicating ledger metadata. Full checkpoint/transition controls pass at 3, 16 and 64 actual source owners/components, plus a larger 0.8-degree source polygon; the unchanged one-owner completed/non-completed controls also pass (six controls total). These establish usable authentic inputs, not a performance improvement or a production-geography claim. Production code remains identical to `93d3a5cc6eaf33364d75d187d45225489118ba3b` for this fixture-only extension.

## Eliminating repeated coordinate grouping

Frozen 93d3 full-route measurements separated the terms: 131,072 supported intervals reduced median RSS from 264,652 to 144,244 KiB while increasing time from 2,096 to 2,822 ms. At 256 source owners/components with only 256 intervals, both old/new paths instead required about 10.3 seconds and 286–289 MiB. A sampled, GC-instrumented profile (excluded from timing comparisons) attributed 812,530 of 823,164 reads to completed append, primarily deriveCoordinateDelta filtering all lazily projected additions once per owner. After-GC heap used was about 14.9 MB, distinguishing allocation churn from retained full geometry.

The continuing fix adds selected ordinal access to the existing repair component index, preserves indexed access through checkpoint addition projection, and groups only ordinals by exact target once. It removes owner-times-component decoding/validation without retaining a geometry cache. The complete old coordinate-delta function is retained as a pinned eager oracle. Nine sequence/index controls and twelve targeted checkpoint/arithmetic controls pass, including exact value/refusal comparisons, a proportional-visit assertion, and genuine 3/16/64-owner transitions. New immutable same-input performance measurements remain pending at this commit.

Largest-object limits remain: the frozen one-owner/one-interval 65,537-point ring case measured 5,873→6,456 ms and 311,840→321,016 KiB, with exact outputs. That shape had no measured memory benefit. These observations do not establish a universal OOM fix.

## Coordinate-array successor (separate from frozen 6582)

The same authenticated parser now spills long coordinate arrays into metadata
vector bodies, using per-depth ordinal indices so nested rings cannot interleave
parent records. Private tagged descriptors preserve JSON values and last-key-wins
semantics; they are not wire-authority inputs. Small coordinate tuples remain
literal, while sequential reads use at most 256 index records and a 64 KiB body
window except an individually larger scalar/element. Hashes still traverse the
semantic values, never substitute raw wire bytes for canonical JSON.

The shared bounds, polygon and native-runtime validators accept branded coordinate
sequences with unchanged numerical algorithms and refusal order. Runtime conversion
still creates Float64 rings and the scanner retains active edge records. Noncoordinate
metadata collections, very large scalars and original source-family acquisition
remain explicit unresolved terms. No universal constant-memory claim is made.

Author tests: 45 parser/grid/sequence controls and 13 genuine completed-entry and
coordinate controls pass. New controls cover nested rings, noncanonical numeric
formatting, duplicate keys, deferred overridden nonfinite values, complete hashes,
closed-store refusal, exact malformed-coordinate messages and a genuine 513-point
source through completed append and numerical comparison. Geometry scale measurements
against the immutable 6582 science are pending at this source checkpoint.

The follow-up geometry consumer audit also covers every supported witness type
(Point/MultiPoint/LineString/MultiLineString/Polygon/MultiPolygon/collections) and
canonical seam views. Lazy coordinate sequences must not leak into the scanner's
required eager polygon/ring roster: native runtime conversion explicitly materializes
those output arrays, and witness accounting consumes every point before reporting
counts. Tests compare complete exact cell predicates, malformed refusals, retained
seam checks and full scanner results for large polygon/ring rosters. The four
ledger/grid/witness/scanner suites pass 120 tests. These tests caught and fixed the
initial successor's LineString admission and lazy-map witness-count gaps.
