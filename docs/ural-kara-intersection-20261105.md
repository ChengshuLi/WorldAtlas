# Kara endpoint from source intersection

The Ural research decision in Neon revision `ural-kara-intersection-20261105`
starts at the unique intersection of the mapped Kara coastline and the first
retained HydroBASINS edge. The former separate 22.13 m coastal connector is
removed. The remaining coordinates match the prior research boundary after
its first two positions. The revised canonical geometry SHA-256 is
`f4943e118ebc42c746d52444e131818dc02828c15c04697294877914d895f9bb`.

`scripts/ural-audit/intersect_kara_coast.py` reproduces the change from the
prior structured geometry and the pinned OSM map extract. It checks both input
digests, requires one interior intersection with the selected coastline way,
rejects an invalid or self-intersecting output, and measures movement using
WGS84 geodesics. Source line topology is coordinate-linear, as in the input
data; this does not add an artificial straight connector. The script produced
identical output and report on two runs. The OSM extract is stored in R2 and
linked as a construction input in Neon. Its R2 readback matches its recorded
SHA-256. The existing HydroBASINS and supporting source links are retained.

The forward and reversed exterior terminal-closure checks, and the Caspian
terminal-closure check, passed against the pinned stage-1 physical mask and
previously selected Caucasus geometry; the proofs are recorded in the boundary
provenance. The adjusted exterior closure used for this check is a local
research derivation, not a selected closure in a complete global revision.
Before using the new boundary in a global pipeline, bind and validate its
closure, source roles and affected region against the then-current selections.
No map rebuild was performed.
