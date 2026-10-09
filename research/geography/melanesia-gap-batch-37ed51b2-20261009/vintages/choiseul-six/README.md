# Choiseul six: source-fit and native-grid handoff

This evidence covers the first six SLB Choiseul candidates in the complete 363-ID operational batch. It does not finish the other 357 candidates.

## What the retained evidence supports

The six original component geometries are covered by one feature in the exact simplified geoBoundaries SLB ADM1 product consumed by `scripts/administrative.py`: feature index 9, shapeID `17018030B68013150931387`, mapped uniquely through retained source metadata to the existing stable Atlas location `gb:SLB:ADM1:17018030B68013150931387` (Choiseul). The compressed source bytes are SHA-256 `bb5015f3111992aaed331dd9eecad792c611d5c6bd6513a7d1f3fd04f82d15c8`; decoded bytes are `418f5f1aeaab5f63d240219d1a78efda66e6ceb35ee1f35345d6e4e55fa0798c`. The bound source feature SHA is `c82b0b46ee74bbefba004675b21fc452e9fd7dab2936ce9d4c5ac572a97c1a10`; its geometry SHA is `56a128a17f304f440cee40409195b976589f4df02e06451ba971d970c5fbc844`.

The exact source-fit rule yields two source-relative geometric proposals:

- `physical-component:6b8adac6ee31bf0283aaaf5676765c5ec0baec0c44df1f4d5d7dab3e57662972`
- `physical-component:d727a2836552df78c6b512a120fdfbb4b7bcda7da08da209e55482a083ab9ec1`

For each, the original candidate equals the exact target union gain, target loss is empty, and no other current geography feature has a new positive-area overlap. The resulting subject geometries are in the admitted run output.

The other four source-supported original candidate geometries are retained for the additive native-grid mechanism. Their exact-coordinate target union overlays do not meet candidate-equals-gain equality, although each case has empty target loss and no positive-area intersection with any other current feature. Two have tiny positive target intersections (`5eb203…`: `3.9652519713989114e-18` degree²; `8e0fe1…`: `1.1032933541941257e-18`; `fbf01e…`: `2.7726874185356684e-18`). The `87db1d…` case has zero measured target-intersection area but still fails exact gain equality. Do not snap, add a tolerance, or use another union experiment to force these into exact geometry proposals. The payloads let engineering test which currently unowned native cells are supported while preserving every existing assignment.

The exclusion query reads and pins all 34 current Atlas geography part files (49,589 unique features). The six-candidate union bbox intersects two current features: Choiseul and the adjacent SLB ADM1 feature `gb:SLB:ADM1:17018030B8659224027401`. None of the six candidates has positive-area intersection with that other feature. This establishes neighbor exclusion for the complete retained baseline geometry, not a whole-world production-pipeline replay.

## Fresh admitted run

The authoritative run is [choiseul-six-exact-003](choiseul-six-exact-003/analysis.json), produced using the repository's pinned `Baseline` and exclusive `NewVintage` evidence helpers. Its `publication.json` is written last and binds every output. `execution.json` records the runtime and exact command; `analyze.py` and `input-pins.json` are copied into that run. Baseline admission accounts for 253,124,582 encoded and decoded input bytes before output publication. Prior exploratory and pre-publication results remain preserved separately and are not treated as the accepted run.

Reproduction uses Python 3.12.14, Shapely 2.1.2 and GEOS 3.13.1. The script's `RUN` constant must be changed to a fresh name before another execution; the helper refuses to overwrite an existing vintage.

The earlier `run-001` receipt, analysis, and stdout are preserved as historical artifacts, but that run is incomplete and unqualified for reproducible custody. Its receipt records a 11,987-byte script with SHA-256 `747ea6781d7cfcec5cf4b0c2342c72a78da16f0484e6a0c34d90a036da790303`; that exact script body is not retained in the packet or branch history. The retained 14,629-byte script (`3ad9a545…`) and archived 11,806-byte provisional script (`e40a8087…`) both differ. The receipt also reports Python 3.7.3 while its command names the Python 3.12 executable. The original receipt and outputs have not been rewritten and no science was rerun to repair this history. Use the separately admitted `choiseul-six-exact-003` vintage for the qualified source-fit results.

## Limits

The represented source year 2021 is not an effective date or proof of current legal authority. Present-day physical ground truth, historic water or ice, processing cause, and boundary authority remain unresolved. These source-relative results support geographic coverage for an existing stable reference location; they do not infer political/legal affiliation, change hierarchy, or authorize publication.
