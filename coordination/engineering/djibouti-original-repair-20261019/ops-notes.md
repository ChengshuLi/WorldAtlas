# DJI original repair operations

## Pinned checkout

- Branch: `engineering/djibouti-original-repair-20261019-01a154ad`
- Input/code commit: `261e709ac9e1837b3399537f9f53cfa6550e3a01`
- Worker identity: `01a154ad-085e-738b-95cf-eb6b663b400f`

## Source-batch extractor sparse input

The current-main reader expects the plain file
`coordination/engineering/global-current-cell-work-queue-20261014/normalized-source-seams.json`.
The first extractor invocation encountered ENOENT on the `.json.gz` spelling;
the full stderr was not retained. I added the existing plain `.json` path to
this worktree's sparse patterns. No reader, source, or shared script was edited,
and no compressed alias was created. Its exact Git object and content hash are
recorded in `source-identity-v1/source-identity-joins.json`.

Successful command:

```sh
node coordination/engineering/global-current-cell-work-queue-20261014/source-batch-intervals.mjs \
  gb-DJI-ADM2--repair-evaluation \
  coordination/engineering/djibouti-original-repair-20261019/source-batch-intervals-v1
```

Result: 683 land cells, 394 intervals, nine targets, across blocks 029 and 030.

The independent selected-owner observer was run at the same commit. Its result
is `selected-owner-observation-v1.json`; it is observational only and reports
zero base, additive, and effective owners for all 683 queried cells.

## Identity evidence boundary

`source-identity-v1/source-identity-joins.json` joins nine original ADM2
Features to their exact queue lineage target IDs and records each queue
`province_id` parent reference. ADM1 names are only candidate context matches
to the parent ID slug: the source ADM2 Features expose no parent identifier.
Both full original DJI source FeatureCollections are retained beside the join
report, including all six ADM1 and eleven ADM2 Features and roster owners.

This evidence establishes identity and queue relationships only. It does not
establish current source applicability, administrative authority, or physical
support. Do not use ADM1 as a negative witness without an exact applicability
finding. The positive source-family roster is the complete ADM2 family.

## Accepted canonical identity stage

`source-stage-v1/original-stage-inputs.json` is a nine-row ordinary JSON array
for the package's exact direct-owner targets. It uses the whole unmodified source
Features from `dji-adm2-source-features.geojson` as `consumed`, and the whole
accepted canonical Features from pinned `data/geography/part-6.json` as
`selected`. `source-stage-v1/canonical-stage-joins.json` records the exact part
pin, all 11 unique full-ID matches against the complete retained ADM2 family,
the 9 target/owner joins and the two complete non-target ADM2 features retained
as context. No owner arithmetic, polygon operation, or Feature subset was used.

The canonical part pin is current-main `261e709ac9e1837b3399537f9f53cfa6550e3a01`,
`data/geography/part-6.json`, blob `4be02d1d055a66c4e1606bab4f23ecda90350f34`,
4,607,953 bytes, SHA-256
`dc494911da2e31191a3e3020006f67a19678a678d0590f379649302d1a2c299a`. Stage
rows are factual identity inputs only; source applicability, physical support,
sovereignty and current authority remain unresolved.

The nine positive stage IDs were also checked against the complete pinned
`data/macro-foundation/world-review-locations-6.json.gz` metadata payload. Its
encoded blob is `306a759a4cf3818f7c086401ac07c1ffdf7ae7e4` (36,853 bytes,
SHA-256 `b7d34bfb646186ecaf767b2627c3ce9fbb9408024a2b1204e448ae0f23d7328`);
decoded JSON is 834,337 bytes, SHA-256
`f82d55547c3524b0343da1d9e0b404c74020d568161379dd8da90801826c734c`. All 11
retained DJI ADM2 IDs occur uniquely at zero-based rows 733–743. For each of the
9 targets, metadata `source_id`, name and parent ID match the exact canonical
Feature; row ordinals and the metadata pin are in `source-stage-v1/canonical-stage-joins.json`.

## Generic physical-support observation

Ran the existing current-main generic command with the committed DJI stage and
verified exact shared physical descriptors/runtime:

```sh
/Applications/ChatGPT.app/Contents/Resources/cua_node/bin/node \
  scripts/prepare-delivery-handoff.mjs physical \
  coordination/engineering/djibouti-original-repair-20261019/physical-config-v1/config.local.json \
  coordination/engineering/djibouti-original-repair-20261019/physical-v1
```

The private local config is SHA-256
`939ce8ae22846ccce82a2da0775d6adee384f131223bafe4bc81cc51eca58743`; its
phase-specific physical config hash in the execution receipt is
`932284f18f383a400c65e4ee48656d096346282af69fc91920cf25c54694fd9c`. It binds
25 consumed input pins: 24 exact records from the accepted shared physical
config (18 encoded source-metadata shards, 3 encoded native shards, the native
member index, comparison method and transport map) plus this committed DJI
stage. The producer refuses unused input pins, so the separately hydrated
seven-blob global physical-source archive is not misrepresented as consumed by
this run. Python 3.12.14, NumPy 2.3.5, Shapely 2.1.2 and GEOS 3.13.1 passed the
actual-file admission check; the inventory was completed with the exact loaded
stdlib files the helper reported as missing before execution.

The existing producer completed in 7.28 seconds, with 18 complete source
metadata receipts and a complete 188,612-record native member. The reviewable
`physical-v1/whole-target-support.json` is 216,083 bytes, SHA-256
`e8cda75ba202bc025b2a609a6b81618e263ac1bb1698114257b2673bbe854dc9`. Its
private `execution-receipt.json` is 586,516 bytes, SHA-256
`a19f4c2bd15e75298eded76eb4b207b4869c1a3819b052526e9867ad7d6e7b92`; the
local `preparation.json` is 545 bytes, SHA-256
`0d9737ec939070654a10bf8764f9b6eda6cd123b186a2891a8fe091e8346a171`. The
receipt and runtime-bearing config remain local because they contain absolute
machine paths; neither is committed or public.

| Owner | Target | Physical flags |
| ---: | --- | --- |
| 16531 | `gb:DJI:ADM2:41766387B13463549189785` | 2: missing and extra reconstruction |
| 16532 | `gb:DJI:ADM2:41766387B22586556456338` | 0 |
| 16533 | `gb:DJI:ADM2:41766387B51204577272085` | 0 |
| 16536 | `gb:DJI:ADM2:41766387B73347270872705` | 3: extra reconstruction, contradictory land/water support, L2 outside L1 |
| 16537 | `gb:DJI:ADM2:41766387B74076707162819` | 1: contradictory land/water support |
| 16538 | `gb:DJI:ADM2:41766387B83981523687012` | 2: missing and extra reconstruction |
| 16539 | `gb:DJI:ADM2:41766387B9467441741428` | 0 |
| 16540 | `gb:DJI:ADM2:41766387B97155389424645` | 1: contradictory land/water support |
| 16541 | `gb:DJI:ADM2:41766387B98599288227121` | 2: missing and extra reconstruction |

These are whole-target, source-relative diagnostics against the retained
physical corpus. A zero-flag row is not source applicability, authority,
sovereignty, native-cell support or package acceptance. Eleven physical flags
occur across six of nine targets. The selected-owner observer remains zero for
all 683 land cells; 394 extracted intervals remain held, with accepted repair
credit 0.

## Source-evidence inputs and foreign context

The factual input assembler is
`source-evidence-v1/prepare-source-evidence-inputs.mjs`. It binds the exact
original denominator (683 land cells and 394 intervals), the nine owner-to-target
rows, the full original `gb:DJI:ADM2` family (11 features), the accepted
canonical part-6 (all 11 direct DJI ADM2 features), the physical report, and the
source-evidence helper. Source membership pins the accepted world index,
semantic report and complete canonical part-6. The complete original DJI ADM1
family (6 features) and two non-target ADM2 Features remain in the earlier
identity/context records. No `territorial_exclusions` field or empty negative
array is supplied.

The stock `source-evidence` phase completed with config SHA-256
`43de8af9628b97d85289f8b2c55369804b2f066d54b954628df15a2cbe1793fa`.
Its `products/source-evidence.json` is 38,598 bytes, SHA-256
`11cd97550794d501998e06e9634ce2f6b43407920ba60e037d5846278d69ac88`; the
preparation receipt is 262 bytes, SHA-256
`ffb3be5808a4ffb370e9216d7f559e43b0939507e65b71c7f50cc8606786fcf1`. The full
original patch is `native-requested-patch.json` (15,961 bytes, SHA-256
`7d2d0f382455c5b5f02e1a3afdcf67eac19b397eefc9cc8c55ce6ce0f5a30833`): 683
exact cells across all 394 intervals. The positive-family roster contains only
the complete `gb:DJI:ADM2` family; ADM1 is not treated as a blanket veto.

The separate `source-context-v1/whole-source-neighbor-context-screen.json`
(9,204 bytes, SHA-256
`0321bd49453837b74f4b9aba03f915e2f51ad7895188763557ae57b7eedc90e7`)
screened complete original ERI, ETH and SOM ADM1/ADM2 families against all nine
DJI target Features using the pinned `coordinateBounds` helper. It found 24
conservative bounding-box candidates across 8 of 9 targets. This does not prove
polygon intersection or political/source applicability. These complete
families remain contextual candidates; specific applicability evidence is not
present, so none is assigned a negative-veto role. The exact contact IDs and
whole-family input pins are in that screen.

The `source-evidence` output is an immutable factual input stage, not a
qualification or accepted delivery. The 24 contextual candidates and existing
physical flags remain unresolved. Native diagnostic, source applicability and
native-authority qualification have not yet run; accepted repair credit remains
0.

The initial native-diagnostic preflight against v1 stopped with `Invalid native
coverage class row`: the package-native validator expects one strictly sorted
coverage row per y coordinate, with multiple runs grouped in that row. No
native diagnostic was produced. The factual v1 source-evidence output remains
preserved as the historical first attempt and is not used for subsequent
native phases. The assembler now groups intervals by y and sorts the runs; it
also writes a distinct v2 packet and refuses to replace the existing context
screen unless its generated bytes match exactly. V2 is the input for native
work. The stock `source-evidence` phase succeeded with config SHA-256
`cf8fa61f4321e799cc336305716cebb1f9c3e96910f986b8aa07136b14262383`; output
is 37,696 bytes, SHA-256
`7225eef7058b2ed5136cc31f5488d3b9daf00088859eb095ffde09ef084611d2`. The
v2 full patch still contains 683 cells and 394 intervals. This format repair
changes no source pins or scientific interpretation.

## Native-diagnostic blocker and independent review

The exact-head review of v2 at `523c774ddf481497d3ea3acb12fdeb0449948b4d`
confirmed the source-evidence output hash and structure: all nine requested
owners, 331 distinct y rows, 394 intervals and 683 cells; the owner set matches
the nine-target roster. The positive family is the complete 11-feature
`gb:DJI:ADM2`; all six DJI ADM1 features and both non-target ADM2 Features are
retained as context. The complete ERI, ETH and SOM ADM1/ADM2 families remain
context only, with 24 conservative bounds candidates across eight DJI targets.
Physical support is bound to the exact reviewed report; its 11 flags across six
targets remain unchanged. The reviewer found no applicability or authority
overclaim and confirmed zero accepted or qualified credit.

The attempted full-scope stock command was:

```
node scripts/prepare-delivery-handoff.mjs native-diagnostic \
  coordination/engineering/djibouti-original-repair-20261019/native-diagnostic-v2/config.json \
  coordination/engineering/djibouti-original-repair-20261019/native-diagnostic-v2/products/native-diagnostic.json
```

It did not produce a diagnostic. The helper reported
`General physical conflict qualification requires explicit territorial exclusions`.
Its pinned check in
`coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs`
requires each selected target with a general physical conflict to carry an
explicit `territorial_exclusions` array. The candidate screen is only a
bounding-box prefilter and supplies no reviewed source-applicability evidence;
therefore no exclusion array is supportable from current evidence. No empty
array or guessed foreign-family veto was added. `native-diagnostic-v2/` contains
only its input config; no diagnostic product exists. The independent reviewer
agreed that stopping here is correct. Since no full-scope diagnostic exists,
`supported-inputs` and `native-authority` were not run; all 683 cells / 394
intervals remain held and accepted repair credit remains zero.

## Exact negative/contact scan inputs (v3)

After reviewer approval of v2, the existing stock `source-evidence` route was
used with `territorial_exclusion_families` set to the six complete original
ERI/ETH/SOM ADM1/ADM2 catalogue products. This uses the documented whole-family
loader and its conservative complete-bounds prefilter; it does not treat the
v2 bounding-box screen as exact contact or adopt source-vintage applicability.
All 683 requested keys and 394 intervals are preserved. The operator emitted
24 exact original geometry operand references over eight targets (per-target
counts: 0, 4, 2, 4, 2, 2, 6, 2, 2); no operand is assigned to the first target.
Each reference is ordinal- and geometry-hash-bound to a complete immutable
family pin. These are exact inputs for the stock native per-cell contact
operator, not legal/source-applicability determinations or accepted vetoes.

The v3 stock `source-evidence` phase succeeded with config SHA-256
`7dd2a8486bb692ff14f6bb67ed6569398570a2eb12d774ad1ed13bff5364d2c6`.
`products/source-evidence.json` is 45,088 bytes, SHA-256
`2fa52699c6b1ae63c79bcb4a8026bb482dad8e85f5f2f4eab8d7322760ea3908`;
`products/territorial-exclusion-provenance.json` is 108,258 bytes, SHA-256
`115d46319d7cf4843913bdd40a60de24962f2fc58de5b9e7e1d2ac1661a1dbf2`.
The output preserves the full six-family source pins and target-level operand
ordinals. Per-cell exact contact counts are not yet available until the native
diagnostic is run. Source-vintage applicability and accepted repair credit
remain unresolved and zero, respectively.

The stock full-scope `native-diagnostic` succeeded against the v3 source evidence
and unchanged complete 683-cell patch. The exact output is 55,938 bytes,
SHA-256 `466671484fab9e939b38257d2340dc88733c7a8351aa3567f68a650e3ee6b13c`;
its preparation receipt binds config SHA-256
`8fa991fc23aebdf0d38c05118f1ef57f3a0879830cc1c5dbb8aaaf26879e2563`.
It reports 683 requested, 683 diagnostic-supported and 0 diagnostic-held
cells over 331 rows. Every requested run has reason `assigned_cells`; thus the
stock exact native source/negative scan reports zero cell-level contacts with
the 24 complete negative operands across these 683 requested cells. This is an
exact cell-screen result, not proof of legal/source applicability and not an
accepted delivery. Per-owner diagnostic counts are: 16531=58, 16532=31,
16533=205, 16536=1, 16537=77, 16538=149, 16539=73, 16540=63, 16541=26.
The diagnostic receipt pins source evidence v3 at commit
`7279490bb94da9ed8e518770c038811d534426d0`, path
`source-evidence-v3/products/source-evidence.json`, SHA-256
`2fa52699c6b1ae63c79bcb4a8026bb482dad8e85f5f2f4eab8d7322760ea3908`; and
full request at commit `523c774ddf481497d3ea3acb12fdeb0449948b4d`, path
`source-evidence-v2/native-requested-patch.json`, SHA-256
`7d2d0f382455c5b5f02e1a3afdcf67eac19b397eefc9cc8c55ce6ce0f5a30833`.
This is still only a diagnostic partition: selected-owner state, per-key source
vintage/applicability, native authority, physical flags, independent delivery
review and acceptance remain separate gates. The original denominator is
preserved and accepted repair credit remains zero.
