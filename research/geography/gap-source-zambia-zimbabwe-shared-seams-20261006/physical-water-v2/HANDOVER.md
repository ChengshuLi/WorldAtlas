# #1234 physical-water continuation handover

## Current checkpoint

- Owned issue: #1234, exactly ten components and four recorded contact subjects; preserve both merged source packets and all original family/unknown records.
- Owned branch: `geography/zmb-zwe-source-1234-r3-20261008`; current pushed code checkpoint before this handover: `307eaac2b550e2ae08ca6af5265a65bc330d942b`.
- The current issue claim is active for worker `01a11551-68d1-7031-a9ac-715eb725a184`; this is the final authorized PR continuation.
- Official ESA WorldCover 2021 v200 source bytes, whole-source limitations, 10 candidate geometries, 21 local contact intersections and two original fragments are retained and pinned. Existing complete comparison sources remain preserved.
- The no-pixel preflight and classification/output-writer controls pass. The classifier path bug is fixed. Its output writer shards complete component/contact records, verifies all output file and bundle caps before writing, and refuses to overwrite prior results.
- No raster pixel has been classified. No actual classification run has started; there is no GIS window or result output yet.

## Admission and limits

`frozen-inputs.json` records 74 pinned inputs / 11,652,764 bytes; per run, 4,074,286 encoded source bytes, 62,914,560 decoded original-block capacity and 932,627 decoded geometry bytes. The 47,518,164-byte source-window crop is theoretical; no crop file is created. The exact conservative one-run static accounting is 176,534,917 bytes against a 256 MiB budget, leaving 91,900,539 bytes for live GEOS/NumPy row geometry and allocator overhead. Loaded Python/GEOS/dyld bodies and the preflight process measurement are recorded there as well.

The current host reported 29% system-wide free memory, below the coordinator’s 40% GIS gate. The fresh storage check passed the checkout/free-space limits. Do not start raster decoding or classification until a fresh explicit window arrives and the live memory gate passes. If a window arrives, stop immediately if RSS exceeds the producer’s 700 MiB abort or any output/temp cap is breached.

WorldCover evidence is limited to its 2021 mapped land-cover classes. Class 80 means mapped permanent water; class 90 remains wetland with water status unresolved; other named classes mean mapped non-water land cover, not proven dry land. The source alone cannot establish a legal shoreline, political ownership, present conditions, or processing cause. Keep unsupported portions unresolved.

## Next work

1. Await the coordinator’s explicit candidate GIS window; do not repeat source acquisition.
2. Under that window, run the complete candidate/contact classification twice with the same frozen inputs and producer, record peak RSS and exact bundle output bytes, then independently compare every shard/hash across both runs.
3. Update the issue-owned evidence manifest with every changed/source/output file, controls and limits; run hosted evidence and all required CI.
4. Obtain distinct exact-head source review, use the serialized merge queue, verify merged mode/blob identity for every changed path, reconcile #1234, release only this claim and clean only the owned managed checkout after durable verification. Keep #1234 open if any original acceptance remains unresolved.

## Coordinator reporting rule

The human explicitly directed GEO workers to message the root coordinator chat `01a10893-2a57-72e0-aa08-5c36088d5206` before becoming idle. Send a concise update when work is complete or when waiting on a live resource/source/review condition. Include the issue/batch, concrete artifact and exact branch/PR/merge/cleanup state, the specific remaining blocker or live handle, and “ready for next batch” only after the assigned work is fully delivered. The human explicitly authorized this worker-to-root message.
