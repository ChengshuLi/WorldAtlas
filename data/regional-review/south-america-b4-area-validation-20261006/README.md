# South America B4 exact area and parent roster validation

Issue: [#1124](https://github.com/ChengshuLi/WorldAtlas/issues/1124). This packet checks the issue's exact 215 location IDs against the immutable #445 workload snapshot and the pinned Atlas hierarchy. It verifies all 39 parent rows, each per-parent membership list, five target area ancestries and complete native-descendant counts. It also compares the relevant portions of the #444 and #446 neighboring worklists against actual hierarchy ancestry. It does not certify the full Chile or Paraguay regions.

## Result

At baseline `93c901e1c0b44073233fd3d48d403985a0cf2c52`, all 215 issue IDs exist in the pinned native parts and map to exactly 39 parents. All parent names, IDs, assigned subjects, counts and nonpartial markers match the native features and hierarchy. The five issue area counts are Chile Central 75, Chile North 29, Chile South 62, Juan Fernández Is. 1 and Paraguay 48. Complete Atlas descendant counts at that baseline are 252, 29, 62, 1 and 243, respectively.

The 230-member #444 snapshot divides into 177 Chile Central and 53 Argentina South members. The 215-member #446 snapshot divides into 195 Paraguay, one Argentina South and 19 Uruguay members. The three worklists together exhaust the five relevant target-area descendant sets at the pinned baseline. Whole neighboring issue totals are not used as target-area denominators.

These are source and identity checks against Atlas's pinned records. They do not independently prove legal boundary status, current completeness, topology, or positional accuracy. No shared geography files are changed.

## Territorial meaning and source review

The crosswalk's WGSRPD values identify botanical distribution units. TDWG describes WGSRPD as a standard for plant distribution recording; its Level 3 botanical countries may disregard purely political considerations, while Level 4 is the basic recording unit. Kew likewise cautions that botanical country units need not match political boundaries. Thus the codes provide source labels and neighboring-granularity context, not administrative parent evidence. The exact retrieved Level 3 and Level 4 table hashes are `7eaf281dfbdca610c93938326c333d7c62d8e82ce3cba63b299d5a3a01d0003f` and `6fa350a0bb5939df0c665ae6cf253ddb0aa85fef6daa684c87ba400faf93b1c2`. Their reuse terms were not established; the raw files are excluded from this commit. See `scope.json` and `evidence-quality.json` for immutable URLs, repository commit, retrieval date and restoration details.

The existing Chile source comparison is geoBoundaries CHL ADM3 vintage 2020, licensed CC BY 3.0 IGO. Its prior review found 345 features versus the official 2023 SUBDERE DPA roster of 346 communes. SUBDERE describes its 2023 political-administrative boundaries as compiled from interior, international and coastline authorities and periodically checked against legal descriptions. Its archive was retained by the earlier packet, but extraction and reuse terms were not resolved here. This packet does not use either dataset to assert boundary correctness.

The existing Paraguay comparison is geoBoundaries PRY ADM2 vintage 2012, licensed CC BY 4.0; its metadata lists 247 features. Paraguay's INE Cartografía Digital 2022 provides current statistical reference material and says its DPA lines are referential for statistical operations. It is not legal boundary evidence. The earlier source review's limited attribute use and attribution terms do not resolve polygon reuse or legal status.

Primary references: [TDWG WGSRPD](https://www.tdwg.org/standards/wgsrpd/), [Kew POWO WGSRPD overview](https://powo.science.kew.org/about), [SUBDERE 2023 DPA publication](https://www.subdere.gov.cl/sala-de-prensa/subdere-publica-nueva-versi%C3%B3n-de-los-l%C3%ADmites-de-la-divisi%C3%B3n-pol%C3%ADtico-administrativa), [SUBDERE IDE dataset](https://ide.subdere.gov.cl/project/division-politico-administrativa-2023/), and [Paraguay INE Cartografía Digital 2022](https://www.ine.gov.py/microdatos/cartografia-digital-2022.php). Exact prior source citations and known retention gaps remain in the original #445 packet; it has not been edited.

## Reproduction

The original TDWG tables are not redistributed. Restore those exact bytes from the raw URLs and immutable source commit identified in `evidence-quality.json`, then verify the two SHA-256 values above. From a checkout containing the pinned baseline objects and these files:

```sh
python3 data/regional-review/south-america-b4-area-validation-20261006/validate_area_crosswalk.py \
  --level3 /path/to/tblLevel3.txt --level4 /path/to/tblLevel4.txt \
  --output-dir data/regional-review/south-america-b4-area-validation-20261006/output
```

The script reads all nine issue-pinned files and the six native geography parts through `git show` at the baseline commit. It also parses the exact TDWG L3/L4 rows through the pinned original reproducer, which derives each source label and name-match field. The candidate crosswalk must reproduce byte-for-byte. The validator runs that original reproduction twice and exercises duplicate, missing, foreign, wrong-name, wrong-count, wrong-area, fabricated-match and rehashed-scope controls. It writes the native subject-parent-area rosters, report and controls.

To create the two complete deterministic output runs and compare whole-file hashes, run:

```sh
python3 data/regional-review/south-america-b4-area-validation-20261006/validate_area_crosswalk.py \
  --level3 /path/to/tblLevel3.txt --level4 /path/to/tblLevel4.txt \
  --output-dir data/regional-review/south-america-b4-area-validation-20261006/output
python3 data/regional-review/south-america-b4-area-validation-20261006/validate_area_crosswalk.py \
  --level3 /path/to/tblLevel3.txt --level4 /path/to/tblLevel4.txt \
  --output-dir data/regional-review/south-america-b4-area-validation-20261006/scratch/run-two-output
python3 data/regional-review/south-america-b4-area-validation-20261006/build_manifest.py
```

The build step requires the first run, second run and restored exact source bytes to be present. It emits `output/reproducibility.json`, input/output whole-file inventories and the evidence manifest. The checked-in packet excludes the raw TDWG tables because their reuse terms remain unknown.

Run the repository checks with Node.js 24:

```sh
node scripts/evidence-quality.mjs data/regional-review/south-america-b4-area-validation-20261006/evidence-quality.json
node scripts/check-handoff-scope.mjs --help
```

The issue's generated handoff contract should also be checked against the actual PR body, and the live premerge manifest validator should be run before submission. See `docs/PREMERGE_EVIDENCE_REVIEW.md` for the serialized queue and exact-head independent review gates.

## Open findings and handoffs

1. The roster and parent audit validates the pinned Atlas hierarchy, not current statutory names, parent status or border alignments. Regional legal-source review is still needed before geographic approval.
2. For Chile, compare all 346 current SUBDERE communes with the 345-feature historical geoBoundaries roster after extracting the 2023 archive and confirming its reuse terms. Resolve the omitted/split/renamed unit, if any, with a sourced correction proposal.
3. For Paraguay, reconcile the 2012 geoBoundaries ADM2 roster with the 2022 INE statistical divisions and current legal administrative units. Treat statistical boundaries as referential; obtain a licensed authoritative legal source for boundary claims.
4. The botanical WGSRPD crosswalk has a distinct purpose and vintage. Keep its source labels separate from political administrative hierarchy.

Each item above is an engineering/research handoff. No whole-region acceptance, geographic approval, import, integration or publication is implied.
