#!/usr/bin/env python3
"""Create the issue-1643 v1 evidence manifest from exact pinned inputs/outputs."""
import gzip, hashlib, json, os, pathlib, subprocess, tempfile
import assemble

BASE = "d07f64b2feab45f4eb2583743da74de91f8bbcce"
ROOT = pathlib.Path(__file__).resolve().parents[3]
OWNED = pathlib.Path("research/geography/melanesia-gap-batch-241e2ce0-20261009")
ROUTING = pathlib.Path("coordination/engineering/global-actionability-routing-20261007")
PHYSICAL = pathlib.Path("coordination/engineering/global-physical-comparison-20261006")
CORPUS = pathlib.Path("coordination/engineering/original-geography-source-corpus-20261006")
COMPONENTS = pathlib.Path("coordination/engineering/physical-gap-components-1005-20261005-local19")
SI = pathlib.Path("research/campaigns/solomon-islands-source-fitness-20261007")
NCL = pathlib.Path("data/regional-review/new-caledonia-valid-province-source-20261005")
IDS = [
"physical-component:a68af90226372a2ffe141464812466f3ce7c4cb2d82332b73736e879e9cfa4e0",
"physical-component:b680fa0be6bb8caf76ed123e423cbc7e7de33d87865cb48bc5d11d416156f45d",
"physical-component:2b39965dae96675fca4577dd52a5bfe9cc7e430f79dfa7089c919bd4ed616af8",
"physical-component:7deb1a01865ea8f87256a5442ca03a55613d4187137d49c1342fdfe33573cb15",
"physical-component:b53c0913a174ea07e07accae42dfcdfe5e9e67810dfaa598398401a8cbd6b890",
"physical-component:9ef68049be5faeccccd1b62178bfd939de8c3226ddbb591070b41b0041a988b8",
"physical-component:91794cfc8c91cd5beafb07cb141172995d941c93eb46c7de72885de9025edfcd",
"physical-component:56489c721bac1766a590d84e12f293bf574fc3d33180dceeb87a09100632e11e",
"physical-component:76f7f6996c0990c4de8bbb3ec27f8a151316532801d32a49d89c603c5f12fe1a",
"physical-component:7b36dfaf63316a134de006b09d006d21fb57632d7359bb0e5b34572738897829",
"physical-component:b45afebcdd32d0f95edb57e8136f432d323c19483ca63fb861b288a959c214d3",
"physical-component:e5eefaf8efe7bce6215613325f8a1173ccbb8ee73f4f0e223c6a7ce4d4ef6abe",
"physical-component:1c0757a8b6119db62215af58de5bf454137c634b347fe48a6a09d44a153fdb94",
"physical-component:f81af9bb2943222d5554fb978efb394f4c24e1bfec12cb4e022c2b58d49fe6d3",
"physical-component:d4b45985f5e76f82c8f4317b6b0453941c4ae25c72a999cdd20d8ec7ce6e3b23",
"physical-component:47375cf5710ddd0ab39b65b283b919cc9a2244d5d9e294fa8f305442c1a67435",
"physical-component:7fd5b82562720e9d1c4e9786704f5467b6883759c94beda5bd0fd77854592550",
"physical-component:b152ead109470c412b34e7eabbd9a56db95b0c8dc3bc027413bf7952c75740f5",
"physical-component:f2e4208cce53c8a178c2a4d457f9dad9a085261cb01e32dbb0c8ac99070bd285",
"physical-component:10f89b3868b4e895d2339368b755f073a626d439640301111352521c9bc24b4b",
"physical-component:721838ee1e1d6c3acde27742d49376d80aeea2a3818aff8ef006e4d407827ebb",
"physical-component:854f216abedb0bc31b01c6cfa93a441c7aed86924b3331c0b61c72c2936733d3",
"physical-component:8bce0affeeb72b155c7df58ba9138fd9cb40ed5134eb25332ef4fcb6c0335d78",
"physical-component:959db9b804312cdfcb293ce59f411d2cb1a279c8e200934290f3937c540a2c85",
"physical-component:a4fddec8ce3ce8a75de023b0b23b966be9de4c9d02f68c579a25e60dda89c68f",
]

def sha(b): return hashlib.sha256(b).hexdigest()
def getbase(path): return subprocess.check_output(["git","show",f"{BASE}:{path.as_posix()}"],cwd=ROOT)
def desc(path):
    raw=getbase(path)
    row={"path":path.as_posix(),"bytes":len(raw),"sha256":sha(raw),"hash_kind":"file-bytes"}
    if raw[:2]==b"\x1f\x8b":
        decoded=gzip.decompress(raw)
        row.update(uncompressed_bytes=len(decoded),uncompressed_sha256=sha(decoded))
    return row
def outdesc(name):
    path=OWNED/name; raw=(ROOT/path).read_bytes()
    return {"path":path.as_posix(),"bytes":len(raw),"sha256":sha(raw),"hash_kind":"file-bytes"}

def safe_replace_manifest(path, raw):
    if path.parent.is_symlink() or not path.parent.is_dir():
        raise RuntimeError(f"Unsafe manifest directory: {path.parent}")
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise RuntimeError(f"Refusing unsafe manifest target: {path}")
    fd, temp_path = tempfile.mkstemp(prefix=".evidence-quality-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if path.is_symlink():
            raise RuntimeError(f"Refusing symlink manifest target: {path}")
        os.replace(temp_path, path)
    finally:
        try: os.unlink(temp_path)
        except FileNotFoundError: pass

def main():
    # Rebuild or verify all packet outputs before binding their hashes.
    assemble.main()
    out=json.loads((ROOT/OWNED/"component-outcomes.jsonl").read_text().splitlines()[0])
    rows=[json.loads(x) for x in (ROOT/OWNED/"component-outcomes.jsonl").read_text().splitlines()]
    assert len(rows)==25 and {x["component_id"] for x in rows}==set(IDS)
    payload_paths=sorted({r["candidate_source"]["path"] for r in rows})
    paths=[
        ROUTING/"evidence-quality.json", PHYSICAL/"results/report.json",
        CORPUS/"evidence-quality.json", SI/"evidence-quality.json",
        SI/"assessment.json", SI/"batch-context.json", SI/"geoboundaries-adm1-source.bin.gz",
        SI/"native-source-records.bin", COMPONENTS/"custody-v1/index.json",
        pathlib.Path("data/geography/part-22.json"), pathlib.Path("data/geography/part-28.json"),
        NCL/"evidence-quality.json", NCL/"findings.md",
    ]+[pathlib.Path(p) for p in payload_paths]
    baseline_files=list({p.as_posix():desc(p) for p in paths}.values())
    bypath={x["path"]:x for x in baseline_files}
    pins={
      "global-actionability-routing-20261007-evidence-quality":"1551d9a51aa7c2407f4ab9733bf2f515aed865670579eb2dbd34d4a405faf3b9",
      "global-physical-comparison-20261006-report":"2a5b59198681d50f577bc4c2c321174f166aec14f57c7564100fc411ae940df0",
      "original-geography-source-corpus-20261006-evidence-quality":"bf06eb5a8fbd869d038a11fb17b6c84e41df7ea6037ab17cded2470054d5c54e",
      "solomon-islands-source-fitness-20261007-evidence-quality":"c10c67e4bee1b0cd468ad6d649690897e2dc636eebd976dd9596aa0ab4031d8b",
    }
    pin_files={
      "global-actionability-routing-20261007-evidence-quality":(ROUTING/"evidence-quality.json").as_posix(),
      "global-physical-comparison-20261006-report":(PHYSICAL/"results/report.json").as_posix(),
      "original-geography-source-corpus-20261006-evidence-quality":(CORPUS/"evidence-quality.json").as_posix(),
      "solomon-islands-source-fitness-20261007-evidence-quality":(SI/"evidence-quality.json").as_posix(),
    }
    for k,v in pins.items(): assert bypath[pin_files[k]]["sha256"]==v, k
    subject_files={r["component_id"]:r["candidate_source"]["path"] for r in rows}
    assert set(subject_files)==set(IDS) and set(payload_paths)<=set(bypath)
    sources=[
      {"id":"GSHHG-2.3.7","url":"https://www.soest.hawaii.edu/wessel/gshhg/","role":"Retained physical reference used in the existing source-relative component analysis.","vintage":"Release 2.3.7 dated 2017-06-15; observation dates heterogeneous or unknown.","retrieved_at":"2026-10-06","license":{"status":"unknown","terms":"Retained documentation differs between LGPL v3 or later and LGPL v3 or any earlier version; no legal interpretation is made."},"retention":"restoration-only","verification":"verified","restoration":"Use exact native record bytes and offsets in the retained #1424 source packet; archive-level restoration is documented there.","limit":"Release date is not observation date. Mapped-land support is source-relative, not physical-land truth or authority.","temporal_status":"unknown"},
      {"id":"gb:SLB:ADM1","url":"https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/SLB/ADM1/geoBoundaries-SLB-ADM1_simplified.geojson","role":"Simplified administrative product used for existing Solomon Islands subject bindings.","vintage":"Represented year 2021; metadata update 2023-01-19; build 2023-12-12; effective date unknown.","retrieved_at":"2026-10-07","license":{"status":"unknown","terms":"The retained product records Natural Earth Public Domain credit and geoBoundaries CC BY 4.0 derivative attribution; underlying particulars are not independently verified."},"retention":"restoration-only","verification":"verified","restoration":"Use the retained product bytes and source assessment from #1424.","limit":"Simplified comparative source with no verified effective date; it does not establish boundary authority or the legal line of a tiny candidate.","temporal_status":"reference"},
      {"id":"gb:IDN:ADM2","url":"https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/IDN/ADM2/geoBoundaries-IDN-ADM2.geojson","role":"Administrative product named by retained Indonesia comparison records.","vintage":"Recorded product metadata vintage 79ffb2ed04702e16f009e4675a8d74ef9bd09d4f; reference year 2020.","retrieved_at":"2026-10-06","license":{"status":"unknown","terms":"This packet adds no product-specific licensing or authority interpretation."},"retention":"restoration-only","verification":"unverified","restoration":"Use the source locator and row binding retained in original routing/source-corpus records.","limit":"Partial/unresolved rows and one missing binding do not establish a unique current target.","temporal_status":"unknown"},
      {"id":"gb:PNG:ADM3","url":"https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/PNG/ADM3/geoBoundaries-PNG-ADM3.geojson","role":"Administrative product named by retained Papua New Guinea comparison records.","vintage":"Recorded product metadata vintage 79ffb2ed04702e16f009e4675a8d74ef9bd09d4f; reference year 2019.","retrieved_at":"2026-10-06","license":{"status":"unknown","terms":"This packet adds no product-specific licensing or authority interpretation."},"retention":"restoration-only","verification":"unverified","restoration":"Use the source locator and row binding retained in original routing/source-corpus records.","limit":"Partial/unresolved rows do not establish a unique current target.","temporal_status":"unknown"},
      {"id":"Natural Earth","url":"https://www.naturalearthdata.com/","role":"Undated modern reference in existing retained source context.","vintage":"Undated modern reference.","retrieved_at":"2026-10-06","license":{"status":"unknown","terms":"Public-domain status is recorded in project metadata; no additional licensing work is done here."},"retention":"restoration-only","verification":"unverified","restoration":"See pinned original geography source-corpus evidence.","limit":"Context only; no new comparison or target assignment is produced.","temporal_status":"reference"},
      {"id":"NCL official and GeoReP evidence","url":"https://georep-dtsi-sgt.opendata.arcgis.com/","role":"Existing New Caledonia source review relevant to contact context.","vintage":"Official BDADMIN-NC 2022; GeoReP item update 2024-10-28.","retrieved_at":"2026-10-06","license":{"status":"unknown","terms":"Retained #911 review reports unresolved redistribution terms for the BDADMIN-NC archive."},"retention":"restoration-only","verification":"verified","restoration":"Use pinned #911 findings and source register; original GeoReP inputs remain byte-preserved and invalid.","limit":"The existing source review and contact context do not prove a unique administrative binding for either batch candidate.","temporal_status":"reference"},
    ]
    output_names=["README.md","assemble.py","finalize_manifest.py","candidate-geometries.geojson","source-target-geometries.geojson","current-target-geometries.geojson","component-outcomes.jsonl","native-ready-inputs.jsonl","family-outcomes.json"]
    manifest={
      "version":1,"issue":1643,"lane":"geography","worker_id":"01a112c1-ac99-74b1-9047-a1da2dd0e245",
      "subject_ids":IDS,"subject_ids_sha256":sha(json.dumps(sorted(IDS),separators=(",",":")).encode()),
      "baseline":{"commit":BASE,"files":baseline_files,"pins":pins,"pin_files":pin_files,"subject_files":subject_files},
      "sources":sources,"outputs":[outdesc(n) for n in output_names],
      "methods":[{"id":"exact-retained-record-join","kind":"code","description":"Selects exact component features from custody-verified components-v3 payloads and joins retained #1424 physical/admin rows. It attaches only already-unique source/current targets. No GIS operation or source acquisition is performed.","software":"Python standard library; Python 3.x","units":"Exact IDs, source record byte offsets, pointset hashes, geometry hashes, and retained row fields."}],
      "metrics":[],"summaries":[],
      "conclusions":[
        {"text":"Five exact components have retained unique compatible Solomon Islands source subjects and mapped-land support; the packet reuses their existing #1424 findings and inputs.","status":"supported","source_ids":["gb:SLB:ADM1","GSHHG-2.3.7"]},
        {"text":"Three components have no retained administrative binding row: two New Caledonia components and one mixed-support Indonesia component. Contact with NCL-1259 does not establish a unique target.","status":"unresolved","source_ids":["NCL official and GeoReP evidence","GSHHG-2.3.7"]},
        {"text":"Other rows retain partial, mixed, outside-context, or unknown dispositions. No target is assigned where subject coverage is unresolved.","status":"unresolved","source_ids":["gb:IDN:ADM2","gb:PNG:ADM3","GSHHG-2.3.7"]},
        {"text":"Physical authority, source observation dates, legal boundary, ownership, and processing cause remain unresolved or unapproved.","status":"unresolved","source_ids":["GSHHG-2.3.7","gb:SLB:ADM1"]}
      ],
      "stages":{"research":"complete","implementation":"not-proposed","geographic_approval":"unapproved"},
      "commands":["python3 research/geography/melanesia-gap-batch-241e2ce0-20261009/finalize_manifest.py"]
    }
    p=ROOT/OWNED/"evidence-quality.json"
    safe_replace_manifest(p,(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n").encode())
    print(json.dumps({"manifest":p.as_posix(),"baseline_files":len(baseline_files),"baseline_bytes":sum(x["bytes"] for x in baseline_files),"outputs":len(output_names),"subject_count":len(IDS),"native_ready_rows":5},indent=2))
if __name__=="__main__": main()
