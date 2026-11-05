# Hypothetical Caucasus land-cell impact on draft 93

Status: 2026-11-05. This is a research screen, not selected geography, an authorized label change, or a current live mismatch count. Both alternative lines and their joins remain geographically uncertain; numerical counts do not establish correctness.

| Alternative | Draft-93 land centers inside bounded faces | Unambiguous hypothetical Asia → Europe | Unambiguous hypothetical Europe → Asia | Ambiguous local side |
| --- | ---: | ---: | ---: | ---: |
| Eastern Qusarçay clipped splice | 56 | 50 | 1 | 5 |
| Western Abin second splice | 113 | 70 | 38 | 5 |

The native grid has width 131072, north 90°, west -180°, and step 360/131072 degrees. Candidate draft-93 row/run SHA-256 values are `a7e7a10d141c7bfc0517b003033114282c97251e77a11329da7d1ca8e023c6c0` and `567ca54891d2bb1ba0977ec0f10c7c0a3f03321253f34dc018c2a1637a03cbcf`. They match the draft-93 handoff manifest. The available candidate labels in every counted center are Asia land (18) or Europe land (19); the current live physical land mask and a later selected candidate build were not available to verify. V7 is a comparison reference, not current ground truth.

Method: polygonize the coordinate-linear selected source line and the exact clipped research alternative and enumerate native cell centers strictly contained in the bounded faces. Read draft-93 and V7 row/run labels for those centers. Classify local sides using WGS84 distances to the original coordinate-linear geometry; multiple closest positions within the search tolerance are treated as ambiguous. This is an impact screen, not a rerun of the full pipeline: affected polygon interiors and locally inferred directions may not exactly reproduce production rasterization, and centers on a line are not counted by strict containment.

The east recalculation used the clipped splice file SHA-256 `ad3ad335d2aa1df8ea347978f063f9b4c2c263832eadcb5b37d6c45237f35427`. It found 19 polygonized faces containing the same 56 cell records as the earlier full exploratory-line screen (which had 20 faces). The earlier 43-cell seeded-model figure concerns an arbitrary smaller study box, not the complete splice impact. All 56 cells are Asia in V7; excluding the 5 ambiguous, 50 hypothetical changes would introduce a mismatch against V7 and 1 would remove one (net +49). This is a comparison with that historical reference, not an error count or prediction of the current total.

The west rerun used second-cut file SHA-256 `f9e4e5da1687f3ffb118e0b621705fe2e6b43a5dc2abbc323699cb56fbf8dcb9`; its 88 faces and 113 records exactly reproduce the earlier screen, whose impact JSON SHA-256 is `443668e1c32ea1df3a79a8677979e181d1ac5679a59a718978519174f44751d2`. Excluding 5 ambiguous centers, 83 hypothetical changes would introduce a mismatch against V7 and 25 remove one (net +58); one of the 5 ambiguous is an existing mismatch.

Thus the western research candidate affects roughly twice as many draft-93 cell centers as the eastern one, but neither has a sufficiently supported continuous watershed and both joins to justify selection. See [the acquisition plan](EVIDENCE-ACQUISITION-PLAN.md) for what could improve the evidence. Recompute with the current selected candidate and physical mask, and run the actual pipeline, before relying on live impact or mismatch changes.
