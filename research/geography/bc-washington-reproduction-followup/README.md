# BC–Washington sample-count reconciliation

Issue #660 assigns three current subjects: Greater Vancouver (`atlas:district:CAN-5915:BRC`), Whatcom County, and San Juan County. This packet preserves the inherited #657 and #485 material and reconciles the narrative against all 18 retained sample rows (IDs 50–67). It does not alter the shared geography or assert a boundary correction.

## Finding

The retained ledger has five rows without strict containment in a 2024 TIGER Washington county polygon: 55, 63, 64, 65 and 66. The inherited prose incorrectly says four. Its first Greater Vancouver distance is stored as 1,011.9 m; formatting to two decimal places gives 1,011.90 m, while inherited prose says 1,011.91 m. The rows identify Greater Vancouver as the nearest current BC location boundary and Whatcom (GEOID 53073) as the nearest Washington county for all 18. These are arithmetic findings about the inherited ledger, not a remeasurement of the original line.

`assessment.json` is the first immutable receipt, generated from the #657 merge commit `a1fd3383e89dea4c4497bf3a6f469494871ad758`. It pins its baseline inputs, validates the complete BC scope and all three assigned subjects with their five-tier parent chains, checks the Statistics Canada (29 BC divisions) and TIGER (39 Washington counties) source rosters, and derives the arithmetic from all 18 inherited rows. The Statistics Canada gzip is 38,880,150 bytes, above the evidence validator's 32 MiB ordinary-file limit; it remains in the preserved #485 packet and is whole-file hash checked from the immutable Git baseline.

The superseding `vintages/ibc-restored-20261004/reproduced-assessment.json` records a source-backed reproduction. Its runner checks the IBC archive and every used baseline input before computation, recreates the full 74-point line sample set, and requires the focused rows 50–67 to match the inherited ledger exactly. The earlier assessment remains unchanged. Run its read-only comparison and controls with:

```sh
/usr/bin/python3 research/geography/bc-washington-reproduction-followup/vintages/ibc-restored-20261004/reproduce.py --archive /path/to/temporary/us-canada-boundary-v1-3.zip
/usr/bin/python3 research/geography/bc-washington-reproduction-followup/vintages/ibc-restored-20261004/verify_restoration.py --archive /path/to/temporary/us-canada-boundary-v1-3.zip
python3 research/geography/bc-washington-reproduction-followup/verify_packet.py
```

## Sources, licenses, method, and limits

- The IBC US–Canada Boundary v1.3, section 25, source metadata is dated 2018-04-20. On 2026-10-04 the official archive URL returned HTTP 200 and the downloaded 258,764 bytes matched SHA-256 `eb327459528b87cbc27e55ccc6bfd6982562c75559823a00b6dc50c04abcaab1`; the downloads index returned 404, but the direct archive endpoint worked. Bundled metadata describes mapping-only use, and the U.S. metadata states © International Boundary Commission, all rights reserved. The archive was used temporarily and is not retained or redistributed. Restore only from the official archive URL, recheck current terms, and verify its whole-file size/hash before use.
- Statistics Canada 2021 Census Divisions are statistical administrative units, vintage 2021; the retained #485 GeoJSON gzip is 38,880,150 bytes, SHA-256 `8a31cf19ad0694638c88275fec9ff1005970cd8600ca6baed245b8826756e9bf`. Statistics Canada Open Licence applies. Their boundaries and codes are statistical reference evidence, not political ownership evidence.
- 2024 Census TIGER/Line Washington counties are U.S. Census Bureau public-domain cartographic data. The retained Washington extract is 859,249 bytes, SHA-256 `74c2822d327082e2738a8d93d59bc5eadf42590f7fef0941221e61deb36a4034`; the inherited upstream archive pin is recorded in #485. The geographic IDs identify source features only.
- The reproduced method projects the IBC line (EPSG:4269) and retained BC, Statistics Canada, and TIGER geometries (EPSG:4326) to EPSG:3347, repairs invalid projected reference geometries using GDAL/OGR `MakeValid`, samples the section at 74 equal intervals no greater than 1 km, and calculates nearest boundaries and strict county polygon containment. The three assigned subjects and complete parent chains, all 61 BC members (including one with no area boundary), 29 Census divisions, and 39 Washington counties are accounted for. The reproduced rows exactly equal all 18 inherited sample rows. Five rows (55, 63–66), not four, have no strict TIGER polygon containment; the minimum is 1,011.90 m when displayed to two decimal places. Source vintages and scales differ. Water/coast representation is a hypothesis only; the evidence does not establish it.

Subject mapping and parent chains remain those pinned in the original source packet. No political ownership, historical attribute, legal boundary, full-region, or import approval is implied. If source restoration later changes any interpretation, open a coordinated follow-up including both BC and Washington neighbors; do not change shared boundaries unilaterally.

The superseding reproduction verifies source availability, pinned inputs, and numerical reproducibility; it does not resolve the coastal offset cause. The older verification files remain as evidence for the original row-only audit. The complete source-vintage results, limitations, and controls are recorded under `vintages/ibc-restored-20261004/`.
