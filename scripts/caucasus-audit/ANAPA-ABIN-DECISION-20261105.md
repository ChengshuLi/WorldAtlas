# Anapa and Abin: source-backed provisional corrections

Status: research candidates, not selected geography. The criterion is the
physical drainage divide, not agreement with a historic label grid. Source and
model limitations below remain material.

## Anapa: prefer the Shingari approach for further verification

The published [Trubetskoy route](https://sashamaps.net/resources/europe-asia-boundary/)
crosses mapped coastline way 396539058 v2 at 37.36792175894848 E,
44.7996329213336 N. Following source feature 462 inland to its first
intersection with the selected boundary gives a 5,360.72 m opening; the join is
37.35088963802999 E, 44.841804886638265 N. The current opening to that join is
8,119.26 m. Concatenation produces a simple whole line and the candidate touches
the retained line only at the join. The selected opening crosses mapped Anapka
water way 38631288 v20 for a 65.02 m geodesic chord; the candidate has no
intersection with 28 complete mapped water-way versions across five archived
OSM extracts. `anapa_author_opening_probe.py` checks these facts and prints all
input hashes.

The 28 ways are not a complete hydrographic inventory, OSM relations are not
checked, and a water-free line is not automatically the divide. The coastline
is a dated mapped feature and not necessarily the selected land input. At
250 m spacing HydroBASINS reports the same modeled terminal on both sides of
the candidate at all 22 stations at 100 and 250 m offsets, while the selected
opening has different terminals at all 33 stations. Coastal basin aggregation
can hide distinct local outlets. This conflict and the unverified local join
prevent selecting the candidate as a proven watershed. The original JAXA tile N044E037 has now been read from R2 and checked as described below; it supports the candidate while leaving the local join unresolved.

## Abin: the second complete splice is the better model-supported candidate

The expanded-Abin SRTM-seeded divide splice runs from 38.31791666666666 E,
44.59583333333336 N to 38.65436563496357 E, 44.50458333333333 N. The
coordinate-linear splice is simple, replaces 44,503.05 m of the selected line
with 61,777.60 m, and derives from named-stream seeds and raw terrain. The first
and second-to-last source intersections define the joins; the final source
intersection has poorer model behavior. Construction and source caveats are in
`west_abin_build_splice_second.py` and the audit synthesis.

At 100 m normal offsets and 200 m stations, JAXA produces expected seed labels
1/2 at 290/309 candidate stations versus 75/223 selected stations; SRTM gives
298/309 versus 82/223. The candidate was constructed from SRTM and the models
share mapped stream seeds, so these are not three independent observations.
At the candidate's east join, source +300 m and candidate -300 m both give 1/2
in all three models at 250 m normal offsets. At the west join, source -300 m
and candidate +300 m both give 1/2 in JAXA and SRTM but 1/3 in Copernicus;
label 3 is unresolved. Sparse samples do not establish both joins or all
headwaters. The alternative is the leading model-supported route, but its
source assembly and joins still require validation before it can replace the
selected, source-reproducible line.

No Neon boundary was changed. These results are not a current grid comparison,
production closure proof, or evidence that an omitted channel does not exist.

## Anapa original JAXA terrain follow-up (2026-11-06)

The original N044E037 ZIP was read from R2 and its SHA-256 matched the catalog:
`2b08d3b51c904473e1d97928afea242974c8faf2eb7f890100b78e91011682fe`.
The WGS84 script `anapa_original_terrain_screen.py` samples both opening
segments every 100 m, using 5x5 DSM medians only where all 25 mask values are 0,
all stack values positive and all heights valid. At 100 m normal offsets the
candidate is center-high at 36 of 46 valid stations (8 invalid), versus 9 of
79 valid stations (3 invalid) on the selected opening. At 250 m offsets it is
center-high at 21 of 27 valid stations (27 invalid), versus 13 of 76 valid
stations (6 invalid). These are samples of a surface, not independent drainage
or proof of a divide, and offshore masking affects the comparison.

Within the last 500 m before the inland join, the final two 100 m-offset and
final four 250 m-offset valid candidate stations are slope-like rather than
center-high. On the first 500 m of the retained continuation, three of six
100 m-offset samples are slope-like or center-low, and at 250 m one is
center-low and two are tied. This weakens the exact geometric join even as the
candidate opening is preferred. The current selected boundary and Neon recipe
are unchanged until a source-supported connection is constructed.

Extracted DSM/MSK/STK SHA-256 values are respectively
`0c69accedecf93f4bc25c6d097485b23923549cdaf5cd29ed5d8e66cecda1ae2`,
`9f261145cd3b1e92cbc3cd7edc7a5c5dd6aae67c0de6e3191ca523f7abea6c2c`, and
`1a45e271fb62180aa217e306ab210e936dcbf4a7925e0cef1331728de8ed0571`.
The candidate and selected cut files used hash to
`9f3b4a04cf08e1f03b881fd66ca2f133993a3e2cb8182e045dd8448740a75b59` and
`a938b95f00723f2fd9cbe8d334f4f61ed6af70e5088e364c59ac402706900e8a`.
