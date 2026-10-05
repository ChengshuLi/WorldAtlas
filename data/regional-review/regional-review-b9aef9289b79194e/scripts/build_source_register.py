#!/usr/bin/env python3
"""Hash retained source bytes and register non-retained authoritative references."""
import hashlib
import json
from pathlib import Path
from source_bytes import source_bytes, source_parts

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "sources"

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

admin = json.loads((ROOT.parents[1] / "administrative-sources.json").read_text())
specs = [
    ("GB-BWA-2015", "gb-BWA-ADM2.geojson", "gb:BWA:ADM2", "Public Domain", "RCMRD", "2015", "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/BWA/ADM2/geoBoundaries-BWA-ADM2.geojson"),
    ("GB-LSO-2017", "gb-LSO-ADM1.geojson", "gb:LSO:ADM1", "Open Data Commons Open Database License 1.0", "OpenStreetMap contributors / Wambacher", "2017", "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/LSO/ADM1/geoBoundaries-LSO-ADM1.geojson"),
    ("GB-NAM-2007", "gb-NAM-ADM2.geojson", "gb:NAM:ADM2", "Public Domain", "Stanford Digital Repository / Namibia Statistics Agency", "2007", "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/NAM/ADM2/geoBoundaries-NAM-ADM2.geojson"),
    ("GB-SWZ-2017", "gb-SWZ-ADM2.geojson", "gb:SWZ:ADM2", "Open Data Commons Open Database License 1.0", "OpenStreetMap contributors / Wambacher", "2017", "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/SWZ/ADM2/geoBoundaries-SWZ-ADM2.geojson"),
    ("GB-ZAF-2020", "gb-ZAF-ADM3.geojson", "gb:ZAF:ADM3", "Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO)", "OCHA Regional Office for Southern and Eastern Africa / South African Municipal Demarcation Board", "2020", "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/ZAF/ADM3/geoBoundaries-ZAF-ADM3.geojson"),
]
retained = []
for evidence_id, filename, key, license_name, attribution, vintage, url in specs:
    raw_source = source_bytes(filename)
    parts = source_parts(filename)
    entry = admin[key]
    retained.append({
        "evidence_id": evidence_id,
        "path": "sources/" + filename if len(parts) == 1 else None,
        "parts": parts,
        "reconstruction": "Concatenate ordered part files byte-for-byte to restore original source bytes; no transformation." if len(parts) > 1 else None,
        "retrieved_utc_date": "2026-10-05",
        "retrieval_url": url,
        "pinned_geoBoundaries_release": "9469f09 (resolved Git commit 9469f09592ced973a3448cf66b6100b741b64c0d)",
        "source_vintage": vintage,
        "source_license": license_name,
        "attribution": attribution,
        "sha256_exact_retained_bytes": hashlib.sha256(raw_source).hexdigest(),
        "bytes": len(raw_source),
        "feature_count": len(json.loads(raw_source)["features"]),
        "baseline_administrative_sources_sha256_field": entry.get("sha256"),
        "baseline_sha256_field_note": "Recorded separately from retained-byte SHA-256; it does not equal this whole GeoJSON byte hash and is not substituted for it.",
    })

arcgis = [
    {
        "evidence_id": "RESOLVE-ITEM-METADATA",
        "path": "sources/arcgis-item-37ea320eebb647c6838c23f72abae5ef.json",
        "retrieved_utc": "2026-10-05",
        "url": "https://www.arcgis.com/sharing/rest/content/items/37ea320eebb647c6838c23f72abae5ef?f=pjson",
        "sha256_exact_retained_bytes": sha(SOURCES / "arcgis-item-37ea320eebb647c6838c23f72abae5ef.json"),
        "license": "CC BY 4.0, as declared in item licenseInfo HTML",
        "finding": "Title RESOLVE Ecoregions and Biomes; description identifies RESOLVE terrestrial ecoregions updated in 2017; public Feature Service.",
    },
    {
        "evidence_id": "RESOLVE-SERVICE-METADATA",
        "path": "sources/arcgis-resolve-ecoregions-service.json",
        "retrieved_utc": "2026-10-05",
        "url": "https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/Resolve_Ecoregions/FeatureServer?f=pjson",
        "sha256_exact_retained_bytes": sha(SOURCES / "arcgis-resolve-ecoregions-service.json"),
        "finding": "FeatureServer layer 0 is Biomes and Ecoregions 2017, polygon geometry, WGS84.",
    },
    {
        "evidence_id": "RESOLVE-SCOPED-ECOREGIONS",
        "path": "sources/arcgis-resolve-scoped-ecoregions.geojson",
        "retrieved_utc": "2026-10-05T13:18:43.356Z",
        "url_template": "https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/Resolve_Ecoregions/FeatureServer/0/query",
        "request": {
            "where": "ECO_NAME IN ('Gariep Karoo','Kalahari Acacia woodlands','Kalahari xeric savanna','Makgadikgadi halophytics','Namib Desert','Namibian savanna woodlands','Zambezian Baikiaea woodlands','Zambezian flooded grasslands','Zambezian mopane woodlands')",
            "outFields": "OBJECTID,FID,ECO_NAME,ECO_ID,BIOME_NAME,REALM",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson",
        },
        "sha256_exact_retained_bytes": sha(SOURCES / "arcgis-resolve-scoped-ecoregions.geojson"),
        "features": 9,
        "license": "CC BY 4.0 per the ArcGIS item metadata above; underlying administrative-source license stays separate",
        "finding": "The numeric resolve suffix matches ECO_ID, not FID or OBJECTID. Each of the 16 scoped geometries matches the referenced geoBoundaries admin feature clipped by the ECO_ID feature at IoU 0.9520–0.9995.",
    },
]

external = [
    {"evidence_id":"BWA-STATSBOTS-2022","title":"Population Housing Census 2022 Administrative and Technical Report","url":"https://www.statsbots.org.bw/sites/default/files/publications/Population%20and%20Housing%20Census%202022-Administrative%20and%20Technical%20Report%20Version%202.pdf","retrieved_utc_date":"2026-10-05","sha256_exact_original_bytes":"eca23da4cb3dfa1dcc1df8b53d6abe5a0790db3dc3c95a329e7f80bd9caf0034","retention":"Only the exact checksum is kept; the PDF itself is not redistributed. Restore via URL and verify SHA-256.","finding":"Table 4 enumerates 28 census districts and separate Sub-District/Admin Authority fields; census areas include city/town districts and divisions, so 'administrative district' is not a safe universal tier inference."},
    {"evidence_id":"LSO-GOV-2022","title":"Lesotho Third National Communication, Chapter 2","url":"https://www.gov.ls/wp-content/uploads/2022/03/Third-National-Communication.pdf","retrieved_utc_date":"2026-10-05","sha256_exact_original_bytes":None,"restoration_note":"Direct response declared 26,096,689 bytes; a bounded 20-second transfer timed out after 3,538,464 bytes. No partial bytes retained. Retrieve the complete PDF later and record its whole-file SHA-256 before reuse.","finding":"Official government report lists ten administrative districts and next-tier 80 constituencies / 124 community councils; Figure 2.3 credits the district map to Lesotho Meteorological Services."},
    {"evidence_id":"NAM-GAZETTE-2013","title":"Government Gazette No. 5261, Proclamation No. 25","url":"https://the-eis.com/elibrary/sites/default/files/downloads/literature/Government%20Gazette%20No%205261.pdf","metadata_url":"https://the-eis.com/elibrary/search/3787","retrieved_utc_date":"2026-10-05","sha256_exact_original_bytes":None,"retention":"Legal instrument used by title/metadata and the reproduced proclamation abstract; no document bytes are retained. Restore the complete Gazette PDF from the attachment link on the EIS record before any geometry use.","finding":"2013 legal proclamation creates Kavango East/West, renames Caprivi Region to Zambezi Region and !Karas Region, and re-divides constituencies."},
    {"evidence_id":"NAM-NSA-2023","title":"Namibia 2023 Population and Housing Census Main Report","url":"https://nsa.org.na/wp-content/uploads/2024/10/2023-Population-and-Housing-Census-Main-Report-28-Oct-2024.pdf","metadata_url":"https://nsa.org.na/document/2023-population-and-housing-census-main-report/","retrieved_utc_date":"2026-10-05","sha256_exact_original_bytes":None,"retention":"No report/map copied; reuse terms were not located. Restore from the Namibia Statistics Agency, inspect its administrative map and record the PDF SHA-256 before boundary use.","finding":"Current official census report maps regional and constituency boundaries; the 2007 retained polygon vintage predates the 2013 legal rearrangement."},
    {"evidence_id":"NAM-ARANDIS-ERONGO","title":"Official Namibia Government / EIA locality and constituency references for Arandis","url":"https://eia.met.gov.na/screening/4489_location_map_2.pdf","additional_primary_url":"https://eia.met.gov.na/screening/4917_scoping_report_profile_energy_epl_8617_updated.pdf","retrieved_utc_date":"2026-10-05","sha256_exact_original_bytes":None,"retention":"No submitted EIA map/report copied. Restore the official registry PDFs; check publisher reuse terms and hash exact response bytes before geometry use.","finding":"The official-hosted EIA source places Arandis in Erongo at approximately 15.16453E, 22.53234S; the scoped Atlas polygon bounds are 20.999–22.504E, 17.822–18.318S and its parent is Caprivi. This is a source-backed location/parent contradiction, not a polygon verdict."},
    {"evidence_id":"NAM-ERONGO-REGIONAL-REPORT","title":"Namibia Index of Multiple Deprivation 2015, National Planning Commission","url":"https://www.npc.gov.na/wp-content/uploads/2023/06/Namibia-Index-of-Multiple-Deprivation-2015.pdf","retrieved_utc_date":"2026-10-05","sha256_exact_original_bytes":None,"retention":"Restoration URL only; no PDF copy retained. Hash the exact original before future use.","finding":"Government table gives Arandis constituency in Erongo Region."},
    {"evidence_id":"SWZ-CURRENT-COUNT-59","title":"Regional Administration, Government of Eswatini","url":"https://swazigov.gov.sz/index.php/ministries-departments/ministry-of-tinkhundla-administration/regional-administration","retrieved_utc_date":"2026-10-05","sha256_exact_original_bytes":None,"retention":"Current web reference only; restore the exact page and record its byte hash before reusing a roster or boundary claim.","finding":"Government page reports 59 Tinkhundla centres across four regions (15, 18, 15, 11)."},
    {"evidence_id":"SWZ-CURRENT-COUNT-55","title":"Tinkhundla Centres, Government of Eswatini","url":"https://www.gov.sz/index.php/tinkhundla-centres","retrieved_utc_date":"2026-10-05","sha256_exact_original_bytes":None,"retention":"Current web reference only; restore the exact page and record its byte hash before reusing a roster or boundary claim.","finding":"Different official government page says 55 Tinkhundla and lists region counts 14, 16, 11, 14. The two current government pages disagree; treat 53 OSM/Wambacher units as incomplete/stale relative to at least one official account and leave the exact current roster unresolved."},
    {"evidence_id":"SWZ-EBC-2017-MAP","title":"2017 Tinkhundla Map, Elections and Boundaries Commission / Government of Swaziland","url":"https://www.gov.sz/images/Tinkhundla/Tinkhundla-Service-Charter-.pdf","retrieved_utc_date":"2026-10-05","sha256_exact_original_bytes":None,"license":"Government copyright notice © 2017; no open redistribution grant found","retention":"Do not retain or redistribute map geometry. Restore from EBC/Government URL for future licensed review; seek an open alternative or explicit permission.","finding":"Official EBC map identifies regional and inkhundla boundaries but the 2017 map alone is not current boundary evidence."},
    {"evidence_id":"SA-STATSSA-2022","title":"Statistics South Africa, district municipal boundary and name change in Eastern Cape (2011–2018)","url":"https://www.statssa.gov.za/publications/Report-03-01-71/Report-03-01-712022.pdf","retrieved_utc_date":"2026-10-05","sha256_exact_original_bytes":None,"retention":"No PDF retained. Restore the official Stats SA report, check use terms and record SHA-256 before geometry use.","finding":"Stats SA reports Cacadu District Municipality renamed Sarah Baartman District Municipality in 2018, with small boundary adjustments in several Eastern Cape districts during the same period."},
    {"evidence_id":"SA-MDB","title":"Municipal Demarcation Board: municipal boundaries and Eastern Cape publications","url":"https://www.demarcation.org.za/municipal-boundaries/","additional_primary_url":"https://www.demarcation.org.za/circulars/","retrieved_utc_date":"2026-10-05","sha256_exact_original_bytes":None,"retention":"No MDB boundary dataset was copied; current product license/reuse terms and exact feature bytes remain unresolved. Restore through the Board's published boundary/redetermination downloads and record exact checksums before use.","finding":"MDB is the statutory independent boundary authority; its official site exposes 2021 municipal boundary redeterminations and later boundary notices, so 2020 boundaries need current revalidation."},
]

baseline_path = ROOT.parents[1] / "administrative-sources.json"
scope_path = ROOT / "source/issue-scope.json"
snapshot_path = ROOT / "source/issue-api-snapshot.json"
output = {
    "version": 1,
    "issue": 435,
    "batch_id": "regional-review:b9aef9289b79194e",
    "retrieval_period_utc": "2026-10-05",
    "baseline": {
        "administrative_sources_path": "data/administrative-sources.json",
        "administrative_sources_sha256": sha(baseline_path),
        "issue_api_snapshot_sha256": sha(snapshot_path),
        "issue_scope_sha256": sha(scope_path),
        "issue_member_ids_sha256": json.loads(scope_path.read_text())["member_location_ids_sha256"],
        "status": "exact immutable source/scope snapshots from current issue and current main; snapshots do not authorize edits outside the packet path",
    },
    "retained_polygon_sources": retained,
    "retained_arcgis_evidence": arcgis,
    "external_primary_references_not_redistributed": external,
    "limitations": [
        "Only retained source files have exact retained-byte SHA-256 values. Null external hashes are explicit missing whole-response hashes, not inferred hashes.",
        "No current authoritative/reusable boundary product was found for the Eswatini current roster or latest Namibia constituencies; source restoration remains an engineering/research handoff.",
        "Source polygons and overlap metrics do not prove legal territorial meaning, current completeness, or island and enclave coverage.",
    ],
}
(ROOT / "findings/source-register.json").write_text(json.dumps(output, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
print("wrote findings/source-register.json")
