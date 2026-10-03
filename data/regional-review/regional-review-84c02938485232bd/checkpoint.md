# Durable checkpoint — 2026-10-03

Issue #494; active reservation `codex-20261003-colombia-batch5-9c5e4d26-26dd-4142-9b50-2b8d020314a4`, claim `bac2ce6d-c0b5-44fd-b575-c60e6632d839`, request `d888aecd-a2f2-44ea-8361-d88496984020`, branch `geography/regional-review-84c02938485232bd`; lease through 2026-10-04T09:41:14Z. Only owned directory is this packet. Branch was rebased on main `4ec44677b5654b1c399fdebaafa35bc038d551ac`; frozen hierarchy/source pins still match.

Completed: 265/265 municipality subjects individually assessed (260 justified, 3 correction-needed name variants, 2 insufficient-evidence invalid overlays); five parent groups individually assessed (four justified, Bogotá label review); official DANE 2024 DIVIPOLA name/code/count crosswalk and 1,015 DANE settlement centers; exact six-packet disjoint partition of all 1,122 Colombia area members; all parent chains; complete retained source/date/license/hash/restoration register. Source/current EPSG:6933 comparisons: 263 valid individual overlays, two invalid; max area difference 5.80%, max symmetric difference 14.37%; parent unions differ 0.256–2.581%. Exact border alignment, outer-envelope coverage, omitted land/islands and fully exhaustive dispersed settlement remain unverified.

Evidence checks passed: `reproduce-audit.py` validates every assignment/source/chain/partition; GDAL/OGR `reproduce-geometry.py` reproduces every stored comparison and department union. Actual issue metadata lane/scope checker passed before commit.

Next: finalize staged changes and generated-data accounting, commit/push, run CI and the serialized squash-merge queue, verify actual merge, release #494 claim, and continue with another ready unclaimed bounded geography issue.
