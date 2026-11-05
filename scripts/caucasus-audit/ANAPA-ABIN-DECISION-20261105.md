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
prevent selecting the candidate as a proven watershed. The quality-screened
JAXA original tile N044E037 is cataloged in R2 but was not accessible in this
executor; a controlled terrain and drainage check is the next decisive step.

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
