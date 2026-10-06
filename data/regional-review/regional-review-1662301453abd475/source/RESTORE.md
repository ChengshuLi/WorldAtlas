# Source restoration and citations

Retrieved 2026-10-05 America/Los_Angeles. The original bytes used by the packet are retained beside this file; exact per-file byte lengths and SHA-256 values are recorded in `geometry-and-membership-results.json` and `evidence-quality.json`. Verify SHA-256 before use. Never overwrite a retained source to refresh it; use a new dated vintage.

## geoBoundaries

Restore ADM2 and ADM1 GeoJSON, metadata, and directory/API records from the immutable commit `9469f09592ced973a3448cf66b6100b741b64c0d` in the [geoBoundaries repository](https://github.com/wmgeolab/geoBoundaries/tree/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/USA). Original GeoJSON URLs:

- `https://raw.githubusercontent.com/wmgeolab/geoBoundaries/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/USA/ADM2/geoBoundaries-USA-ADM2.geojson`
- `https://raw.githubusercontent.com/wmgeolab/geoBoundaries/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/USA/ADM1/geoBoundaries-USA-ADM1.geojson`

The release metadata names Census MAF/TIGER and the 2018 Cartographic Boundary product, with Public Domain source data. Preserve the [geoBoundaries citation and use notice](https://github.com/wmgeolab/geoBoundaries/blob/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/USA/ADM2/CITATION-AND-USE-geoBoundaries.txt); attribute geoBoundaries under CC BY 4.0 as that notice requests, and credit the Census Bureau. The source's Public Domain metadata does not waive attribution for the geoBoundaries derivative.

## Census 2018 cartographic files

Original files are at the official [Census 2018 cartographic boundary download page](https://www.census.gov/geographies/mapping-files/2018/geo/carto-boundary-file.html). Direct archive URLs:

- `https://www2.census.gov/geo/tiger/GENZ2018/shp/cb_2018_us_county_500k.zip`
- `https://www2.census.gov/geo/tiger/GENZ2018/shp/cb_2018_us_state_500k.zip`
- `https://www2.census.gov/geo/docs/maps-data/maps/reg_div.txt`

These are U.S. federal Census products; retain Census source credit. Census describes cartographic boundaries as simplified for small-scale thematic mapping, warns that small areas can be omitted, and says they should not be used for area/perimeter analysis or precise geographic relationships. The separate [TIGER/Line 2018 documentation](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.2018.html) distinguishes the detailed statistical files and their Jan. 1, 2018 vintage. Neither statistical depiction establishes jurisdictional ownership or legal boundary authority.

## Census TIGERweb extracts

The retained JSON layer and map metadata identify the service and layer vintage. The extracted feature responses were retrieved from these official endpoints on the date above; parameters are URL encoded as shown:

- 2018 counties: `https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS2018/MapServer/84/query?where=STATE%20in%20('19'%2C'27')&outFields=*&returnGeometry=true&f=geojson&outSR=4326`
- 2018 states: `https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS2018/MapServer/82/query?where=STATE%20in%20('19'%2C'27')&outFields=*&returnGeometry=true&f=geojson&outSR=4326`
- 2026 counties: `https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/82/query?where=STATE%20in%20('19'%2C'27')&outFields=*&returnGeometry=true&f=geojson&outSR=4326`
- 2026 states: `https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/80/query?where=STATE%20in%20('19'%2C'27')&outFields=*&returnGeometry=true&f=geojson&outSR=4326`

Compressed county responses are retained exactly as returned. Their uncompressed GeoJSON sizes and digests are independently recorded. TIGERweb metadata labels the 2018 and 2026 vintages and Census source. Census requests attribution; its generalized 2018 Cartographic Boundary product caveats must not be transferred to TIGERweb's detailed layer as if the products were interchangeable.

## Reproduction

From repository root, use a clean isolated Python environment and install `data/regional-review/regional-review-1662301453abd475/requirements.txt`, then run `PYTHONPATH=. python data/regional-review/regional-review-1662301453abd475/reproduce.py`. The script reads retained files only, performs no network requests, and writes only the packet's `geometry-and-membership-results.json`. It imports the immutable shared geometry helper from `scripts/evidence/`; the script does not alter input geometry or Atlas source data.

## Related GitHub issue-scope snapshots

The exact public GitHub API responses for sibling West North Central work items #261, #263, and #265 are retained as `issue-261-api-snapshot.json`, `issue-263-api-snapshot.json`, and `issue-265-api-snapshot.json`. They were retrieved on 2026-10-05 America/Los_Angeles from `https://api.github.com/repos/ChengshuLi/WorldAtlas/issues/{number}`. They reproduce task-scope comparison only and are not geographic sources. The reproduction checks their scoped states and counts (119, 198, and 115) against the other five states; with #264's 186 these sum to the full 618-location division scope. Treat these as dated snapshots and do not overwrite them when refreshing.
