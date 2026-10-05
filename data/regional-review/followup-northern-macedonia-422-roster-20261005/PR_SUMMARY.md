# PR summary: North Macedonia 84-to-80 roster research

This source-only packet completes issue #995’s bounded research acceptance for all 84 pinned `gb:MKD:ADM2` subjects and the eight existing parent relationships. It records an ID-preserving crosswalk to the SSO’s 2019 NTES roster, restoration instructions and exact hashes for sources that cannot be redistributed, the retained CC-BY HDX/RIMWGE original, reproducible geometry/name comparisons, and explicit engineering handoffs. It does not certify legal boundaries or approve a hierarchy change.

Key findings:

- 84 legacy polygons crosswalk to 80 NTES municipality codes: 79 one-to-one matches plus five Kichevo-related legacy polygons (four units absorbed into Kichevo and the old Kichevo polygon).
- All eight existing parents correspond to SSO level-3 statistical regions, which SSO describes as non-administrative groupings.
- The source `SHN4` code is non-unique in Kichevo and Skopje. Three source/native label differences are separately reported for Debarca, Mavrovo i Rostuse, and Gazi Baba.
- The exact legal epoch of the 2016 geometry, AKN reuse terms/vintage, and large Resen and Dojran area residuals remain unresolved. No boundary correction is proposed from those comparisons.

Reproduce with the environment documented in the packet:

```sh
python data/regional-review/followup-northern-macedonia-422-roster-20261005/reproduce.py
node scripts/evidence-quality.mjs data/regional-review/followup-northern-macedonia-422-roster-20261005/evidence-quality.json .
python data/regional-review/followup-northern-macedonia-422-roster-20261005/geometry-controls.py
node --test test/evidence-quality.test.mjs test/premerge-evidence.test.mjs
```

Closes #995
