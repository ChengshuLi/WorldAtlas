# Jvari Pass: mapped channel and terrain check

Research lead only. Selected boundary and grid labels are unchanged; no replacement is selected.

A direct OpenStreetMap API bbox extract (2026-11-05) contains complete way 83809279 v8, an unnamed stream tagged source "1:50 000 Topo". Its coordinate-linear geometry intersects the selected boundary at approximately 44.455110995°E, 42.508090947°N, close to the previous Jvari terrain-sample point. Its downstream endpoint node 975735930 is shared with named Bidara/Baidara river way 83809194 v15; that way ends at node 975735947, where Bidara river 169427255 v12 continues to node 1806432303, shared with Terek river way 1137646800 v1. This is mapped OSM topology, not a surveyed confirmation of the stream or real-world flow. Two other locally mapped streams, ways 1286864372 v1 and 1298640853 v1, also cross the selected line. Their exact outlets remain unverified. The bbox extract is incomplete as a regional hydrographic census.

At WGS84 along-way offsets -500,-300,-200,-100,-50,0,+50,+100,+200,+300,+500 m relative to the intersection, the Copernicus GLO-30 DSM samples in way direction are 2421.60, 2395.60, 2388.38, 2381.34, 2382.12, 2378.93, 2378.15, 2373.82, 2369.50, 2366.03 and 2363.01 m. All sampled pixels have EDM1 FLM2 WBM0. Values generally decline downstream, with a 0.78 m local rise from -100 to -50 m. Surface heights are not flow observations, and individual samples do not validate neighboring pixels.

A separate WGS84 strict D8 screen on the same Copernicus DSM starts along the mapped stream at offsets -500,-400,-300,-200,-100,-50,+50,+100,+200,+300 m. All eight-neighbor 3x3 windows must have EDM1 FLM2 WBM0, slope distances use WGS84 geodesics, the original coordinate-linear selected line is preserved, and no filling is performed. Upstream starts at -300,-200,-100,-50 m cross the selected line and subsequently stop in pits or flats; -500 and -400 m stop before crossing, and downstream starts do not cross. These are correlated routes through the same DSM, not an independent outlet observation. Script jvari_stream_d8_screen.py reproduces them. The cross-section and along-channel evidence strengthens the Jvari discrepancy lead, but a mapped line and unconditioned surface model do not establish the exact divide or a connected correction. Obtain independent drainage mapping, construct and check any continuous alternative and evaluate impacts before deciding.

Raw OSM extracts, including the node/ways responses that support the mapped chain, are locally packaged as jvari-osm-evidence-20261105.zip SHA-256 f4bb376316463277c0d8a6dbf11a2bd49a935c4657a52dc3a3543b6e0774b1dc. The previously downloaded Copernicus tile and quality masks, with source URLs and hashes, are described in SEGMENT-REVIEW-20261105.md. These raw files are now archived in R2 and byte-hash readback verified using the existing authorized OAuth session; see the source manifest below. Do not put temporary research-only records into the production Neon pipeline.


## Original JAXA comparison and source manifest

The existing R2 object sources/jaxa/alos-world-3d-30m/v4.1/original/N042E044.zip was retrieved (18,404,177 bytes, SHA-256 68d911703e76f008d705cf97c7a69ae5a5fc944629cd1b92c3f555951ca9e615); ZIP integrity passed and it contains DSM, MSK and STK. The coordinator independently read the same R2 object and confirmed the SHA-256 and the presence of DSM, MSK and STK. JAXA product information and access: https://www.eorc.jaxa.jp/ALOS/en/dataset/aw3d30/ .

At -500,-300,-200,-100,-50,0,+50,+100,+200,+300,+500 m along the same mapped channel, original DSM heights are 2428,2401,2392,2386,2387,2383,2381,2381,2375,2370,2368 m. All 11 sampled 5x5 neighborhoods have MSK0 and STK>0; the sampled center stack count is 3 throughout. The 5x5 median heights are 2428,2401,2395,2389,2388,2386,2383,2381,2377,2373,2369 m, monotonically nonincreasing. Strict unconditioned WGS84 D8 starting at -500,-400,-300,-200,-100,-50 m crosses only from -50 m; every route stops at a local pit or flat, and positive-offset starts do not cross. This source independently corroborates general downslope terrain across the mapped line, but does not independently demonstrate actual runoff or prove a corrected watershed. Script jvari_stream_jaxa_screen.py reproduces the screen.

All the following are research inputs only; none is a pipeline input or a selected structured-data record. R2 readback SHA-256 matched every listed source. The raw XML package contains the public OSM bbox response https://api.openstreetmap.org/api/0.6/map?bbox=44.44,42.495,44.47,42.520 and the node/ways responses for 975735930, 975735947, 1806432303, 975736375, 975735732 and 12029869914. It preserves the mapped channel topology for reproducibility, not an approved boundary.

| Research source and R2 key | Bytes | SHA-256 |
|---|---:|---|
| sources/osm/caucasus-central/jvari-evidence-20261105-f4bb37631646.zip | 113063 | f4bb376316463277c0d8a6dbf11a2bd49a935c4657a52dc3a3543b6e0774b1dc |
| sources/copernicus/dem/glo-30/aws-cog/n42-e044/DEM-4adeff7502b8.tif | 41735106 | 4adeff7502b8eec38a72a3330ffd94adc1207d334469c343fccae9b536deffb2 |
| sources/copernicus/dem/glo-30/aws-cog/n42-e044/EDM-5aa85d4b32b9.tif | 885212 | 5aa85d4b32b901bcaaead74d35d4a40c4bde5151698408f1778323a0538dd684 |
| sources/copernicus/dem/glo-30/aws-cog/n42-e044/FLM-60098898be88.tif | 888723 | 60098898be8800f8ba118a4c29d78d8ddad1b7c434351b032baa4ec9524091ba |
| sources/copernicus/dem/glo-30/aws-cog/n42-e044/WBM-e1cfb64cf186.tif | 32079 | e1cfb64cf186c5be71f4d16a42d5152928b3f319217cd88402fe988c226cf0ae |
| sources/mountaineering/anokhin-east-caucasus-route52-49216b8dcf3d.html | 70382 | 49216b8dcf3dbc94e19d8993ee837df967364adc471e7dec77b374f8ee200c2e |

Copernicus DEM source URL is in SEGMENT-REVIEW-20261105.md; its EDM/FLM/WBM are in the same source tile directory's AUXFILES subdirectory, with product names ending _EDM.tif, _FLM.tif and _WBM.tif. Anokhin mirror: https://veskavkaz.narod.ru/lib/eastkavkaz/index6.html . The mirror supplies regional historical drainage context for the eastern research lead, not pipeline data.
