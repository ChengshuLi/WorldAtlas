# England coastal tile: research comparison

This is one native-grid tile, not a global comparison or an approved geography. The candidate is a partial 12-nautical-mile coastal layer; open ocean remains unassigned and the historical distance, coast and tie conventions are unverified. Candidate generation did not read historical V2 labels. V2 was read only for comparison.

The 131,072 × 54,614 center-sampled grid tile covers columns `[64512, 65536)` and rows `[12288, 13312)`. Of 152,191 candidate coastal-water cells, 151,432 have the same continental-water code as the preserved V2 grid; 759 are ocean in V2. There were zero cells with a different continental-water code, zero V2 continental-water cells absent from the candidate band, and zero physical land/water class mismatches in this tile. These counts do not establish geographic correctness or behavior elsewhere. The tile completed in approximately 6.36 seconds on the test machine; this is not a global runtime estimate.

## Evidence pins

SHA-256 digests identify the exact inputs and reports. Paths from the local research machine are omitted. Reproduction requires separately obtaining the pinned physical, land and historical V2 streams; this note does not distribute them.

- Physical rows: `6cf4b928b6609b4d9c8fdd9264bb6f463a38a5d7376d6ffb0ffc43502284a468`
- Physical runs: `1396fe9dfde48b65b6e5884089a5445682511fb47f9560ce06edd53c95d928d7`
- Candidate land rows: `a7e7a10d141c7bfc0517b003033114282c97251e77a11329da7d1ca8e023c6c0`
- Candidate land runs: `2c67f4c4f31dfe109cbfdf3bfb0704c8960d6e5ff6bd2457e14d2356026969d6`
- Candidate land report: `1269f7e7f3cf11b15d82bc5b06c34535bf2543c52189a22e38e043e437eec801`
- Preserved V2 reference rows: `f254d5ace508252f1a250d72e62073093b9ad8d0e1a6a6a66e6db96aa7f70a7f`
- Preserved V2 reference runs: `1ea99e7823944d2510681c2e257e0db62b3fdfc8009c34abeb7222b3f6f5aef2`
- Original tile report: `1d5763326b801c7876ec5dee469e6922fb3272110797332c1f374200cc5c8692`
- Original comparison report: `32fee559d512176982e6d014f219f02305f3b28d1bf6d3851018677397f5675c`
- Candidate span file: `a7b957e65b4a27f2fe66109e4ab833d5c10fbac56801432e605efbd5e4634de9`

The tile uses the `coastal_band.py` research method: inclusive 12 nautical miles by spherical distance to a physical-grid land/water edge, with the lowest continent code winning ties within 0.00001 metres. The original reports also pin the exact code files and configuration; their digests above identify those unmodified reports, which are not included here.
