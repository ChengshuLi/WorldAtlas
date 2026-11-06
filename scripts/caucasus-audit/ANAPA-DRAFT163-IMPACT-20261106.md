# Anapa bounded draft163 impact

The two alternative opening cuts share their inland endpoint. A local diagnostic
compared their coordinate-linear geometry on the 131072 x 54614 draft163
physical mask, west -180, north 90, step 360/131072 degrees. It polygonized
the two cuts plus a four-neighbor path through water-cell centers and used an
even/odd rule to handle their multiple intersections. It counted **229 land
cell centers** in the resulting difference area.

An independent water-center path via an offshore waypoint gave the same exact
229 land-center coordinates (zero set difference), though the number of
enclosed water centers changed from 22 to 937. This sensitivity check is not
a production physical-water closure proof. The candidate coastal endpoint
falls within a land-classified cell; the short connection from that terminal
to an adjacent water center was not independently validated. The mask is the
verified draft163 stand-in, not a confirmed latest physical generation. Do
not use this diagnostic as the final current-grid count or as authorization
to change selected geometry.

Reproduce with `anapa_draft163_impact.py`, once the hash-pinned inputs are
available; run once normally and once with `--offshore-waypoint`. The two
cut GeoJSON byte hashes are selected
`8c001c61c46ced35905239eccdc4f17b16858df0e1cb76b3e7815f3d61cfde3b`
and candidate
`1c30e158f222ffe2c23293e69a69a99a1d8fbcf03f6032cb8401d320d94628bc`.
The selected and proposed full lines, source decisions and joins are described
in `CAUCASUS-COMPARISON-20261106.md` and the Anapa candidate assembler.
Physical rows hash:
`6cf4b928b6609b4d9c8fdd9264bb6f463a38a5d7376d6ffb0ffc43502284a468`;
physical runs hash:
`1396fe9dfde48b65b6e5884089a5445682511fb47f9560ce06edd53c95d928d7`.

The selected Neon boundary was not modified and no global map was rebuilt.
