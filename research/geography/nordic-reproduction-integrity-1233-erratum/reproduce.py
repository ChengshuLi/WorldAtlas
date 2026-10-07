#!/usr/bin/env python3
"""Authenticated, phase-bounded reproduction for geography issue #1389.

Reads only immutable Git objects named by source-lock.json. New outputs are
admitted as an exclusive directory below vintages/<run-id> before work starts.
"""
from __future__ import annotations
import argparse, gzip, hashlib, json, math, os, pathlib, re, shutil, stat, subprocess, sys, tempfile
import types
from datetime import datetime, timezone

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LOCK_PATH = HERE / "source-lock.json"
RAW_LIMIT = 32 * 1024 * 1024
PHASE_LIMIT = 256 * 1024 * 1024
PREPARATION_HELPER = None


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canon(value) -> bytes:
    if PREPARATION_HELPER is not None:
        return PREPARATION_HELPER.canonical_json(value)
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode()


def git_blob(commit: str, path: str) -> bytes:
    if PREPARATION_HELPER is not None:
        PREPARATION_HELPER.safe_path(path)
    if not re.fullmatch(r"[0-9a-f]{40}", commit) or path.startswith("/") or ".." in pathlib.PurePosixPath(path).parts:
        raise ValueError("unsafe immutable object reference")
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{commit}:{path}"])


def decode_pin(pin):
    raw = git_blob(pin["commit"], pin["path"])
    if len(raw) != pin["bytes"] or sha(raw) != pin["sha256"]:
        raise ValueError(f"whole-file pin mismatch: {pin['id']}")
    if len(raw) > RAW_LIMIT:
        raise ValueError(f"raw file exceeds 32 MiB: {pin['id']}")
    decoded = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
    if len(decoded) > RAW_LIMIT:
        raise ValueError(f"decoded file exceeds 32 MiB: {pin['id']}")
    return raw, decoded


def verify_pinned_bytes(raw, byte_count, digest, label):
    if len(raw)!=byte_count or sha(raw)!=digest:
        raise ValueError(f"pinned bytes changed: {label}")


def require_area_match(actual, expected, label):
    if not math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-14):
        raise ValueError(f"measurement differs from retained result: {label}")


def negative_measurement_control(expected):
    perturbed=expected+1e-6
    try: require_area_match(perturbed,expected,"perturbed measurement control")
    except ValueError: return {"case":"perturbed-area-metric","rejected":True,"absolute_perturbation":1e-6}
    raise ValueError("measurement control accepted a deliberately perturbed area")


def json_pin(pin):
    raw, decoded = decode_pin(pin)
    val = json.loads(decoded)
    return val, {"id": pin["id"], "commit": pin["commit"], "path": pin["path"],
                 "bytes": len(raw), "sha256": sha(raw), "decoded_bytes": len(decoded),
                 "decoded_sha256": sha(decoded)}


def load_complete_components(pins, expected_ids):
    """Scan every original shard, bind four exact full features and lineage."""
    found = {}
    receipts = []
    scanned = 0
    for number in range(7, 18):
        pin = pins[f"baseline_{number}"]
        obj, rec = json_pin(pin)
        receipts.append(rec)
        scanned += len(obj.get("features", []))
        for feature in obj.get("features", []):
            fid = feature.get("id")
            if fid in expected_ids:
                if fid in found:
                    raise ValueError(f"duplicate component id: {fid}")
                found[fid] = feature
    if set(found) != set(expected_ids):
        raise ValueError("complete component family does not contain the exact four-id roster")
    expected_fc, _ = json_pin(pins["original_1233_12"])
    expected = {f.get("id"): f for f in expected_fc.get("features", [])}
    if set(expected) != set(expected_ids) or len(expected_fc.get("features", [])) != 4:
        raise ValueError("retained original component roster is not exact and unique")
    for fid in expected_ids:
        if canon(found[fid]) != canon(expected[fid]):
            raise ValueError(f"original component geometry/properties/lineage mismatch: {fid}")
    return found, receipts, scanned


def verify_inventory_families(pins):
    inventory, inv_receipt=json_pin(pins["baseline_3"])
    descriptors={d["sha256"]:d for d in inventory.get("source_descriptors",[])}
    expected={
      "components":[pins[f"baseline_{i}"] for i in range(7,18)],
      "fragments":[pins[f"baseline_{i}"] for i in range(18,35)],
      "contacts":[pins["baseline_35"]]}
    receipts={}
    for family,pinned in expected.items():
        products=inventory.get("complete_products",{}).get(family,[])
        if len(products)!=len(pinned): raise ValueError(f"inventory {family} product roster count mismatch")
        product_by_hash={x["sha256"]:x for x in products}
        if len(product_by_hash)!=len(products): raise ValueError(f"inventory {family} product duplicate hash")
        if set(product_by_hash)!={p["sha256"] for p in pinned}:
            raise ValueError(f"issue-pinned file family differs from complete inventory: {family}")
        family_rows=[]
        for pin in pinned:
            product=product_by_hash[pin["sha256"]]
            alias=inventory.get("custody_aliases",{}).get(product["path"])
            descriptor=descriptors.get(pin["sha256"])
            resolved=alias or (descriptor["path"] if descriptor else None)
            if descriptor is None or descriptor["path"]!=resolved or pin["path"]!=resolved or product["bytes"]!=pin["bytes"]:
                raise ValueError(f"inventory source path/size does not bind exact whole-file pin: {pin['id']}")
            raw,decoded=decode_pin(pin)
            if len(decoded)!=product.get("uncompressed_bytes") or sha(decoded)!=product.get("uncompressed_sha256"):
                raise ValueError(f"inventory decoded-byte provenance mismatch: {pin['id']}")
            family_rows.append({"pin_id":pin["id"],"inventory_path":product["path"],"custody_path":alias,
              "raw_bytes":product["bytes"],"sha256":product["sha256"],
              "decoded_bytes":product.get("uncompressed_bytes"),"decoded_sha256":product.get("uncompressed_sha256")})
        receipts[family]=family_rows
    return inventory,inv_receipt,receipts


def load_complete_fragments(pins, components):
    expected_hashes = {}
    for component in components.values():
        for binding in component.get("properties", {}).get("fragment_bindings", []):
            fid = binding.get("id")
            digest = binding.get("feature_sha256")
            if not fid or not digest or (fid in expected_hashes and expected_hashes[fid] != digest):
                raise ValueError("component fragment bindings are missing or contradictory")
            expected_hashes[fid] = digest
    found={}; receipts=[]; scanned=0
    for number in range(18,35):
        obj, rec=json_pin(pins[f"baseline_{number}"]); receipts.append(rec)
        features=obj.get("features",[]); scanned += len(features)
        for feature in features:
            fid=feature.get("id")
            if fid in expected_hashes:
                if fid in found: raise ValueError(f"duplicate referenced fragment id: {fid}")
                if sha(canon(feature)) != expected_hashes[fid]:
                    raise ValueError(f"fragment geometry/provenance hash mismatch: {fid}")
                found[fid]=feature
    if set(found)!=set(expected_hashes):
        raise ValueError("complete fragment family is missing a referenced feature")
    retained,_=json_pin(pins["original_1233_13"])
    retained_features=retained.get("features",[])
    retained_by_id={f.get("id"):f for f in retained_features}
    if len(retained_by_id)!=len(retained_features) or set(retained_by_id)!=set(found):
        raise ValueError("retained fragment evidence roster differs from live component bindings")
    if any(canon(retained_by_id[fid])!=canon(found[fid]) for fid in found):
        raise ValueError("retained fragment feature differs from complete-family scan")
    return found, receipts, scanned


def load_complete_contacts(pins, components, fragments):
    contacts, receipt=json_pin(pins["baseline_35"])
    cids=set(components); fids=set(fragments)
    selected=[row for row in contacts if any(x in cids for x in row.get("components",[])) or any(x in fids for x in row.get("fragments",[]))]
    old,_=json_pin(pins["original_1233_14"])
    expected=old.get("component_inputs",{}).get("source_rows_matching_component_refs",[])
    if canon(selected)!=canon(expected):
        raise ValueError("complete contact product join differs from retained scoped contact rows")
    return selected, receipt, len(contacts)


def source_comparison_for_country(iso, source_fc, atlas_c, atlas_m, components, registry):
    from shapely.geometry import shape, mapping
    from shapely import union_all
    id_prefix=f"gb:{iso}:ADM2:"
    source={id_prefix+str(f.get("properties",{}).get("shapeID")):f for f in source_fc.get("features",[])}
    if len(source)!=len(source_fc.get("features",[])) or len(source)!=({"NOR":431,"SWE":290}[iso]):
        raise ValueError(f"complete {iso} source product has unexpected count or duplicate feature ids")
    for fid,feature in source.items():
        props=feature.get("properties",{})
        if not props.get("shapeID") or props.get("shapeGroup")!=iso or props.get("shapeType")!="ADM2":
            raise ValueError(f"whole-product shape identity/tier mismatch: {fid}")
    selected=[fid for fid in source if fid in components.get("subjects",{})]
    expected_ids={x for x in components["subjects"] if x.startswith(id_prefix)}
    if set(selected)!=expected_ids or len(expected_ids)!=(3 if iso=="NOR" else 1):
        raise ValueError(f"{iso} exact subject features absent from complete source product")
    cfeatures={f.get("id"):f for f in atlas_c.get("features",[]) if f.get("id") in expected_ids}
    mfeatures={f.get("id"):f for f in atlas_m.get("features",[]) if f.get("id") in expected_ids}
    if set(cfeatures)!=expected_ids or set(mfeatures)!=expected_ids:
        raise ValueError(f"{iso} selected Atlas identity missing in a C/M vintage")
    subject_rows=[]
    for fid in sorted(expected_ids):
        sf=source[fid]; cf=cfeatures[fid]; mf=mfeatures[fid]
        if sf.get("properties",{}).get("shapeID")!=fid.rsplit(":",1)[-1]:
            raise ValueError(f"source feature shapeID does not bind exact Atlas id: {fid}")
        sg=shape(sf["geometry"]); cg=shape(cf["geometry"]); mg=shape(mf["geometry"])
        if not sg.is_valid or not cg.is_valid or not mg.is_valid:
            raise ValueError(f"invalid geometry in exact subject: {fid}")
        parent_id=cf.get("properties",{}).get("parent_id")
        expected_parent={"NOR":"framework:province:troms-og-finnmark:38859f82963b","SWE":"framework:province:norrbottens-lan:a6d0306eee4c"}[iso]
        meta=cf.get("properties",{}).get("metadata",{})
        if parent_id!=expected_parent or mf.get("properties",{}).get("parent_id")!=expected_parent:
            raise ValueError(f"parent identity differs from exact C/M evidence: {fid}")
        if meta.get("source_role")!="Municipality" or meta.get("administrative_level")!="ADM2" or meta.get("parent_source_level")!="ADM1":
            raise ValueError(f"declared source role or tier differs from exact C-vintage feature: {fid}")
        if canon(cf)!=canon(mf): raise ValueError(f"selected whole C/M feature differs for {fid}")
        subject_rows.append({"id":fid,"source_full_feature_sha256":sha(canon(sf)),"atlas_C_full_feature_sha256":sha(canon(cf)),
          "atlas_M_full_feature_sha256":sha(canon(mf)),"source_geometry_sha256":sha(canon(sf["geometry"])),
          "atlas_C_parent_id":parent_id,"atlas_M_parent_id":mf.get("properties",{}).get("parent_id"),
          "recorded_source_role":meta.get("source_role"),"recorded_administrative_level":meta.get("administrative_level"),
          "recorded_parent_source_level":meta.get("parent_source_level"),
          "atlas_C_geometry_sha256":sha(canon(cf["geometry"])),"atlas_M_geometry_sha256":sha(canon(mf["geometry"])),
          "C_M_subject_feature_identical":canon(cf)==canon(mf),"source_C_geometry_identical":canon(sf["geometry"])==canon(cf["geometry"]),
          "source_C_topologically_equal":sg.equals(cg),"symmetric_difference_planar_area":sg.symmetric_difference(cg).area,
          "atlas_C_minus_source_geometry":mapping(cg.difference(sg)),"source_minus_atlas_C_geometry":mapping(sg.difference(cg))})
    union=union_all([shape(f["geometry"]) for f in source_fc["features"]])
    per_component=[]
    for fid,feature in sorted(components["candidates"].items()):
        geom=shape(feature["geometry"]); inter=geom.intersection(union); diff=geom.difference(union)
        perunit=[]
        for source_id,sf in source.items():
            sg=shape(sf["geometry"])
            if geom.intersects(sg):
                contact=geom.intersection(sg)
                if not contact.is_empty:
                    dim=2 if contact.area>0 else (1 if contact.length>0 else 0)
                    perunit.append({"source_feature_id":source_id,"shapeName":sf.get("properties",{}).get("shapeName"),
                      "contact_kind":["point-only-contact","positive-length-contact","positive-area-overlap"][dim],
                      "intersection_dimension":dim,"intersection_planar_area":contact.area,
                      "intersection_planar_length":contact.length,"intersection_geometry":mapping(contact)})
        per_component.append({"id":fid,"candidate_planar_area":geom.area,"product_intersection_planar_area":inter.area,
          "product_difference_planar_area":diff.area,"product_intersection_geometry":mapping(inter),
          "product_difference_geometry":mapping(diff),"intersecting_adm2_units":perunit})
    return {"iso":iso,"complete_feature_count":len(source),"registry_metadata":registry,
      "subject_feature_comparisons":subject_rows,"component_overlays":per_component,
      "country_union_geometry":mapping(union),"subject_source_geometries":{fid:source[fid]["geometry"] for fid in sorted(expected_ids)},
      "source_subject_features":[source[fid] for fid in sorted(expected_ids)],
      "atlas_C_subject_features":[cfeatures[fid] for fid in sorted(expected_ids)]}


def combined_source_overlays(country_results, components):
    from shapely.geometry import shape, mapping
    from shapely import union_all
    full_union=union_all([shape(country_results[iso]["country_union_geometry"]) for iso in ("NOR","SWE")])
    contact_union=union_all([shape(g) for iso in ("NOR","SWE") for g in country_results[iso]["subject_source_geometries"].values()])
    rows=[]
    for fid,feature in sorted(components.items()):
        geom=shape(feature["geometry"])
        both_i=geom.intersection(full_union); both_d=geom.difference(full_union)
        contact_i=geom.intersection(contact_union); contact_d=geom.difference(contact_union)
        rows.append({"id":fid,"all_two_source_products_intersection_planar_area":both_i.area,
          "all_two_source_products_difference_planar_area":both_d.area,
          "all_two_source_products_intersection_geometry":mapping(both_i),
          "all_two_source_products_difference_geometry":mapping(both_d),
          "four_contact_union_intersection_planar_area":contact_i.area,
          "four_contact_union_difference_planar_area":contact_d.area,
          "four_contact_union_intersection_geometry":mapping(contact_i),
          "four_contact_union_difference_geometry":mapping(contact_d)})
    return rows


def load_physical_inputs(pins):
    # These are retained Natural Earth references used by the earlier physical
    # producer. The double gzip land source intentionally has two layers.
    land_pin, lake_pin = pins["baseline_41"], pins["baseline_39"]
    raw_land = git_blob(land_pin["commit"], land_pin["path"])
    if len(raw_land) != land_pin["bytes"] or sha(raw_land) != land_pin["sha256"]:
        raise ValueError("physical land outer-byte pin mismatch")
    layer1 = gzip.decompress(raw_land)
    land_bytes = gzip.decompress(layer1)
    if len(layer1)>RAW_LIMIT: raise ValueError("physical land intermediate gzip member exceeds 32 MiB")
    if len(land_bytes) > RAW_LIMIT:
        raise ValueError("physical land decoded file exceeds 32 MiB")
    land = json.loads(land_bytes)
    lake, lake_receipt = json_pin(lake_pin)
    return land, lake, {
        "land": {"id": land_pin["id"], "commit": land_pin["commit"], "path": land_pin["path"],
                 "outer_bytes": len(raw_land), "outer_sha256": sha(raw_land),
                 "intermediate_bytes": len(layer1), "decoded_bytes": len(land_bytes),
                 "decoded_sha256": sha(land_bytes), "feature_count": len(land.get("features", []))},
        "lakes": lake_receipt,
    }


def physical_reproduction(components, land, lakes):
    # Re-enter the original numerical operation on the authenticated exact rows.
    from shapely.geometry import shape, mapping
    from shapely import union_all, __version__ as shapely_version, geos_version_string
    land_union = union_all([shape(f["geometry"]) for f in land["features"]])
    lake_union = union_all([shape(f["geometry"]) for f in lakes["features"]])
    rows=[]
    for fid in sorted(components):
        geom=shape(components[fid]["geometry"])
        li=geom.intersection(land_union); ld=geom.difference(land_union)
        ki=geom.intersection(lake_union); kd=geom.difference(lake_union)
        rows.append({"component_id":fid,"candidate_planar_area":geom.area,
          "natural_earth_land_intersection_area":li.area,"natural_earth_land_difference_area":ld.area,
          "natural_earth_land_intersection_geometry":mapping(li),"natural_earth_land_difference_geometry":mapping(ld),
          "natural_earth_lakes_intersection_area":ki.area,"natural_earth_lakes_difference_area":kd.area,
          "natural_earth_lakes_intersection_geometry":mapping(ki),"natural_earth_lakes_difference_geometry":mapping(kd)})
    return {"source_bindings": {"land": "authenticated complete retained Natural Earth input", "lakes": "authenticated complete retained Natural Earth input"},
      "results":rows,"software":{"shapely":shapely_version,"geos":geos_version_string},
      "limits":["Natural Earth generalized physical references do not establish authoritative hydrology, ice, coastline, boundary assignment, or source-vintage truth.",
      "Planar square-degree intersections only; a nonzero land overlap does not prove the remaining candidate portion is land."]}


def negative_component_controls(components, ids, land, lakes):
    """Exercise the same admission/calculation boundary with real malformed rows."""
    controls=[]
    valid=set(ids)
    def admit(rows):
        got=[f.get("id") for f in rows]
        if len(got)!=len(set(got)) or set(got)!=valid or len(got)!=4:
            raise ValueError("exact unique component roster required")
        for f in rows:
            if canon(f)!=canon(components[f["id"]]):
                raise ValueError("component geometry or lineage differs from authenticated whole feature")
        physical_reproduction({f["id"]:f for f in rows},land,lakes)
    good=[components[i] for i in ids]
    cases={"missing":good[:-1],"duplicate":good+[good[0]],
      "fabricated_id":[dict(good[0],id="physical-component:"+"f"*64)]+good[1:],
      "wrong_geometry":[dict(good[0],geometry={"type":"Point","coordinates":[0,0]})]+good[1:],
      "wrong_fragment_lineage":[dict(good[0],properties=dict(good[0]["properties"],fragment_bindings=[{"id":"physical-gap:fabricated","feature_sha256":"0"*64}]))]+good[1:]}
    for name,rows in cases.items():
        before=len(controls)
        try: admit(rows)
        except (ValueError,KeyError): pass
        else: raise ValueError(f"negative control was accepted: {name}")
        controls.append({"case":name,"rejected_before_result":True,"no_result_emitted":len(controls)==before})
    return controls


def safe_output(run_id, root=None):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{7,63}", run_id):
        raise ValueError("run id must be 8-64 lowercase letters, digits or dashes")
    base = pathlib.Path(root) if root is not None else HERE / "vintages"
    if PREPARATION_HELPER is not None:
        PREPARATION_HELPER.safe_path("vintages/" + run_id)
    base.mkdir(mode=0o700, exist_ok=True)
    if base.is_symlink() or not base.is_dir():
        raise ValueError("vintages path is not a real directory")
    target = base / run_id
    target.mkdir(mode=0o700, exist_ok=False)
    root_st = base.stat(follow_symlinks=False)
    target_st = target.stat(follow_symlinks=False)
    if not stat.S_ISDIR(root_st.st_mode) or not stat.S_ISDIR(target_st.st_mode):
        raise ValueError("exclusive output admission failed")
    return base, target, (root_st.st_dev, root_st.st_ino), (target_st.st_dev, target_st.st_ino)


def exclusive_output_controls():
    vintages=HERE/"vintages"
    vintages.mkdir(mode=0o700,exist_ok=True)
    observed=[]
    with tempfile.TemporaryDirectory(prefix=".admission-controls-",dir=vintages) as tmp:
        root=pathlib.Path(tmp)/"vintages"
        root.mkdir()
        # Occupied directories and both kinds of symlink are rejected without touching their target.
        for case,run_id in (("ordinary","ordinary01"),("symlink","symlink01"),("broken-symlink","broken-symlink01")):
            target=root/run_id; sentinel=root/(case+"-sentinel")
            sentinel.write_text("foreign-preserved\n")
            if case=="ordinary":
                target.mkdir(); (target/"sentinel").write_text("foreign-preserved\n")
            elif case=="symlink": os.symlink(sentinel,target)
            else: os.symlink(root/"missing",target)
            try: safe_output(run_id,root=root)
            except (FileExistsError,NotADirectoryError,ValueError): pass
            else: raise ValueError(f"occupied destination was accepted: {case}")
            if sentinel.read_text()!="foreign-preserved\n": raise ValueError(f"foreign sentinel changed: {case}")
            if case=="ordinary" and (target/"sentinel").read_text()!="foreign-preserved\n": raise ValueError("ordinary foreign directory changed")
            if case in ("symlink","broken-symlink") and not target.is_symlink(): raise ValueError(f"symlink replaced: {case}")
            observed.append({"case":case,"rejected_without_mutation":True})
        # A caller cannot escape through a traversal-shaped run id.
        escaped=root.parent/"escape-target"; escaped.write_text("foreign-preserved\n")
        try: safe_output("../escape-target",root=root)
        except ValueError: pass
        else: raise ValueError("path traversal run id was accepted")
        if escaped.read_text()!="foreign-preserved\n": raise ValueError("escaped sentinel changed")
        observed.append({"case":"escaped-run-id","rejected_without_mutation":True})
        # Existing files collide under O_EXCL, and a replacement directory is detected before writes.
        base,out,bid,oid=safe_output("race-probe-0001",root=root)
        existing=out/"result.json"; existing.write_text("foreign-preserved\n")
        try: atomic_new(base,out,bid,oid,"result.json",b"new\n")
        except FileExistsError: pass
        else: raise ValueError("existing output file was overwritten")
        if existing.read_text()!="foreign-preserved\n": raise ValueError("existing output sentinel changed")
        old=pathlib.Path(str(out)+"-held"); out.rename(old); out.mkdir()
        replacement=out/"foreign.txt"; replacement.write_text("replacement-preserved\n")
        try: atomic_new(base,out,bid,oid,"partial.json",b"new\n")
        except ValueError: pass
        else: raise ValueError("replacement run directory was accepted")
        if replacement.read_text()!="replacement-preserved\n": raise ValueError("replacement directory content changed")
        observed.extend([{"case":"occupied-output-file","rejected_without_mutation":True},
          {"case":"replaced-run-directory","rejected_without_mutation":True}])
        # Replacing the vintages ancestor with a symlink is rejected before creating a target there.
        external=root.parent/"external"; external.mkdir(); outside_sentinel=external/"sentinel"; outside_sentinel.write_text("foreign-preserved\n")
        symlink_root=root.parent/"symlink-vintages"; os.symlink(external,symlink_root)
        try: safe_output("under-symlink-0001",root=symlink_root)
        except ValueError: pass
        else: raise ValueError("symlink output ancestor was accepted")
        if outside_sentinel.read_text()!="foreign-preserved\n" or (external/"under-symlink-0001").exists():
            raise ValueError("outside sentinel changed through symlink ancestor")
        observed.append({"case":"symlink-ancestor","rejected_without_mutation":True})
    return observed


def atomic_new(base, target, root_id, target_id, rel, data):
    if PREPARATION_HELPER is not None:
        PREPARATION_HELPER.safe_path(rel)
    parts = pathlib.PurePosixPath(rel).parts
    if not parts or any(p in ("", ".", "..") for p in parts):
        raise ValueError("invalid output path")
    if (base.stat(follow_symlinks=False).st_dev, base.stat(follow_symlinks=False).st_ino) != root_id:
        raise ValueError("output root was replaced")
    if (target.stat(follow_symlinks=False).st_dev, target.stat(follow_symlinks=False).st_ino) != target_id:
        raise ValueError("run directory was replaced")
    parent = target
    for component in parts[:-1]:
        parent = parent / component
        parent.mkdir(mode=0o700, exist_ok=True)
        st = parent.stat(follow_symlinks=False)
        if not stat.S_ISDIR(st.st_mode):
            raise ValueError("non-directory output ancestor")
    dfd = os.open(parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
    try:
        name = parts[-1]
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600, dir_fd=dfd)
        try:
            with os.fdopen(fd, "wb", closefd=True) as f:
                f.write(data); f.flush(); os.fsync(f.fileno())
        except BaseException:
            try: os.unlink(name, dir_fd=dfd)
            except OSError: pass
            raise
        os.fsync(dfd)
    finally:
        os.close(dfd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args()
    lock = json.loads(LOCK_PATH.read_text())
    contract_bytes=(HERE/"issue-contract-source.txt").read_bytes()
    verify_pinned_bytes(contract_bytes,len(contract_bytes),lock["issue_body_sha256"],"captured GitHub issue contract")
    pins = {p["id"]: p for p in lock["pins"]}
    if len(pins) != 57 or set(lock["subject_ids"]) != {
        "gb:NOR:ADM2:86288312B50158709887361", "gb:NOR:ADM2:86288312B64496782861055",
        "gb:NOR:ADM2:86288312B82966611739072", "gb:SWE:ADM2:70781695B94600430897975"}:
        raise ValueError("contract roster/pin count mismatch")
    # Authenticate the actual helper before computation and reject modified bytes.
    helper = lock["authenticated_helper"]
    helper_bytes = git_blob(helper["commit"], helper["path"])
    verify_pinned_bytes(helper_bytes,helper["bytes"],helper["sha256"],"shared immutable helper")
    global PREPARATION_HELPER
    pinned_helper = types.ModuleType("worldatlas_pinned_immutable")
    exec(compile(helper_bytes, helper["path"], "exec"), pinned_helper.__dict__)
    if pinned_helper.VERSION != "worldatlas-evidence-preparation-v1":
        raise ValueError("pinned immutable helper version mismatch")
    PREPARATION_HELPER = pinned_helper
    try: verify_pinned_bytes(helper_bytes+b"# altered helper control\n",helper["bytes"],helper["sha256"],"altered helper control")
    except ValueError: helper_control={"case":"altered-helper-bytes","rejected_before_output":True}
    else: raise ValueError("altered helper bytes passed authentication")
    # Pin audit is split by semantic family; phase accounting includes raw and decoded bytes.
    groups = {
        "components": [f"baseline_{i}" for i in range(7, 18)],
        "fragments": [f"baseline_{i}" for i in range(18, 35)],
        "contacts": ["baseline_35"],
        "source_and_vintages": ["original_1233_3", "original_1233_4", "actual_comparison_part-17", "actual_comparison_part-22", "baseline_2"],
        "retained_evidence": ["baseline_1", "baseline_3", "baseline_4", "baseline_5", "baseline_6", "baseline_36", "baseline_37", "baseline_38", "baseline_39", "baseline_40", "baseline_41"] + [f"original_1233_{i}" for i in range(1, 15)],
    }
    family_records = {}
    raw_total = decoded_total = 0
    for family, ids in groups.items():
        records=[]; raw_n=decoded_n=0
        for pid in ids:
            raw, dec = decode_pin(pins[pid])
            rec={"id":pid,"commit":pins[pid]["commit"],"path":pins[pid]["path"],"bytes":len(raw),"sha256":sha(raw),"decoded_bytes":len(dec),"decoded_sha256":sha(dec)}
            records.append(rec); raw_n += rec["bytes"]; decoded_n += rec["decoded_bytes"]
        # The implementation and this family's serialized receipt are charged to the phase.
        code_n = len(pathlib.Path(__file__).read_bytes()) + len(LOCK_PATH.read_bytes())
        result_n = len(canon(records))
        total = raw_n + decoded_n + code_n + result_n
        if total > PHASE_LIMIT:
            raise ValueError(f"{family} phase exceeds 256 MiB: {total}")
        family_records[family] = {"files":records,"raw_bytes":raw_n,"decoded_bytes":decoded_n,"code_bytes":code_n,"result_bytes":result_n,"phase_bytes":total}
        raw_total += raw_n; decoded_total += decoded_n

    # Whole source/comparison files and the exact old measurement record are preserved as pins.
    prior, prior_pin = json_pin(pins["original_1233_14"])
    old_physical, old_physical_pin = json_pin(pins["original_1233_7"])
    inventory, inventory_pin, inventory_families=verify_inventory_families(pins)
    source_products={}
    for iso,pid in (("NOR","original_1233_3"),("SWE","original_1233_4")):
        obj, rec=json_pin(pins[pid]); fs=obj.get("features",[])
        source_products[iso]={"pin":rec,"feature_count":len(fs),"ids":[f.get("id") for f in fs],"shape_ids":[f.get("properties",{}).get("shapeID") for f in fs]}
    # Independently check whole Atlas vintages and exact subject features at C and M.
    byid={}
    for pid in ("actual_comparison_part-17","actual_comparison_part-22","baseline_5","baseline_6"):
        obj,rec=json_pin(pins[pid])
        for f in obj.get("features",[]):
            if f.get("id") in lock["subject_ids"]: byid.setdefault(pid,{})[f["id"]]=sha(canon(f))
    # Reserve the entire new output vintage before any geometry calculation.
    output_controls=exclusive_output_controls()
    base,out,base_id,out_id=safe_output(args.run_id)
    started=datetime.now(timezone.utc).isoformat()
    component_features, component_receipts, component_scanned = load_complete_components(pins, lock["component_ids"])
    fragment_features, fragment_receipts, fragment_scanned = load_complete_fragments(pins, component_features)
    selected_contacts, contact_receipt, contact_count = load_complete_contacts(pins, component_features, fragment_features)
    source_bundle={"subjects":{fid:None for fid in lock["subject_ids"]},"candidates":component_features}
    # Reconstruct all four source/Atlas subject comparisons against each full national
    # source product and both genuine Atlas file vintages, one country per phase.
    source_results={}; source_phase_bytes={}
    registry, registry_receipt=json_pin(pins["baseline_2"])
    for iso, source_pid, c_pid, m_pid in (
        ("NOR","original_1233_3","actual_comparison_part-17","baseline_5"),
        ("SWE","original_1233_4","actual_comparison_part-22","baseline_6")):
        source_fc, source_rec=json_pin(pins[source_pid])
        atlas_c, c_rec=json_pin(pins[c_pid]); atlas_m, m_rec=json_pin(pins[m_pid])
        # The complete part files are consumed and authenticated even though only
        # the four declared subject IDs are extracted for exact comparisons.
        source_results[iso]=source_comparison_for_country(iso,source_fc,atlas_c,atlas_m,
            {"subjects":source_bundle["subjects"],"candidates":component_features},registry[f"gb:{iso}:ADM2"])
        phase_inputs=[source_rec,c_rec,m_rec,registry_receipt]
        p_raw=sum(x["bytes"] for x in phase_inputs)+prior_pin["bytes"]
        p_dec=sum(x["decoded_bytes"] for x in phase_inputs)+prior_pin["decoded_bytes"]
        p_result=len(canon(source_results[iso])); p_components=len(canon(component_features)); p_code=len(pathlib.Path(__file__).read_bytes())
        p_total=p_raw+p_dec+p_result+p_components+p_code
        if p_total>PHASE_LIMIT: raise ValueError(f"complete {iso} source semantic phase exceeds 256 MiB: {p_total}")
        source_phase_bytes[iso]={"raw_bytes":p_raw,"decoded_bytes":p_dec,"derived_component_bytes":p_components,"code_bytes":p_code,"result_bytes":p_result,"phase_bytes":p_total,"limit":PHASE_LIMIT,"pins":phase_inputs}
    combined_overlays=combined_source_overlays(source_results,component_features)
    combined_phase_bytes=len(canon(source_results["NOR"]["country_union_geometry"]))+len(canon(source_results["SWE"]["country_union_geometry"]))+len(canon(source_results["NOR"]["subject_source_geometries"]))+len(canon(source_results["SWE"]["subject_source_geometries"]))+len(canon(combined_overlays))+len(canon(component_features))+len(pathlib.Path(__file__).read_bytes())
    if combined_phase_bytes>PHASE_LIMIT: raise ValueError("combined-source overlay phase exceeds 256 MiB")
    expected_subjects={r["id"]:r for r in prior.get("subject_feature_comparisons",[])}
    for iso,result in source_results.items():
        for row in result["subject_feature_comparisons"]:
            expected=expected_subjects[row["id"]]
            if row["source_full_feature_sha256"]!=expected["consumed_source_full_feature_sha256"] or row["atlas_C_full_feature_sha256"]!=expected["atlas_full_feature_sha256"] or row["source_C_topologically_equal"]!=expected["topologically_equal"]:
                raise ValueError(f"fresh source/Atlas subject measurements differ from retained evidence: {row['id']}")
            require_area_match(row["symmetric_difference_planar_area"],expected["symmetric_difference_planar_area"],row["id"])
    expected_components={r["id"]:r for r in prior.get("full_product_overlays",[])}
    for iso,result in source_results.items():
        key="norway_full_product" if iso=="NOR" else "sweden_full_product"
        for row in result["component_overlays"]:
            expected=expected_components[row["id"]][key]
            require_area_match(row["product_intersection_planar_area"],expected["intersection_planar_area"],f"{iso}/{row['id']}/intersection")
            require_area_match(row["product_difference_planar_area"],expected["difference_planar_area"],f"{iso}/{row['id']}/difference")
    for row in combined_overlays:
        expected=expected_components[row["id"]]
        metric_keys=("all_two_source_products_intersection_planar_area","all_two_source_products_difference_planar_area","four_contact_union_intersection_planar_area","four_contact_union_difference_planar_area")
        for key in metric_keys: require_area_match(row[key],expected[key],f"{row['id']}/{key}")
    measurement_control=negative_measurement_control(expected_components[lock["component_ids"][0]]["all_two_source_products_intersection_planar_area"])
    land,lakes,physical_pins=load_physical_inputs(pins)
    physical=physical_reproduction(component_features,land,lakes)
    physical_controls=negative_component_controls(component_features,lock["component_ids"],land,lakes)
    # Compare the measured rows to the independent retained physical producer result.
    if canon(physical["results"]) != canon(old_physical.get("results", [])):
        raise ValueError("fresh physical measurements differ from the retained original result")
    component_raw=sum(x["bytes"] for x in component_receipts)
    component_dec=sum(x["decoded_bytes"] for x in component_receipts)
    physical_code_bytes=len(pathlib.Path(__file__).read_bytes())
    physical_result_bytes=len(canon(physical))
    component_expected_bytes=len(canon(component_features))
    comp_expected_pin=pins["original_1233_12"]
    comp_expected_raw,comp_expected_dec=decode_pin(comp_expected_pin)
    component_phase=component_raw+component_dec+inventory_pin["bytes"]+inventory_pin["decoded_bytes"]+len(comp_expected_raw)+len(comp_expected_dec)+physical_code_bytes+physical_result_bytes+component_expected_bytes
    fragment_raw=sum(x["bytes"] for x in fragment_receipts)
    fragment_dec=sum(x["decoded_bytes"] for x in fragment_receipts)
    fragment_result_bytes=len(canon({fid:sha(canon(f)) for fid,f in fragment_features.items()}))
    fragment_feature_bytes=len(canon([fragment_features[fid] for fid in sorted(fragment_features)]))
    frag_expected_raw,frag_expected_dec=decode_pin(pins["original_1233_13"])
    fragment_phase=fragment_raw+fragment_dec+inventory_pin["bytes"]+inventory_pin["decoded_bytes"]+len(frag_expected_raw)+len(frag_expected_dec)+physical_code_bytes+fragment_result_bytes+fragment_feature_bytes+component_expected_bytes
    contact_phase=contact_receipt["bytes"]+contact_receipt["decoded_bytes"]+inventory_pin["bytes"]+inventory_pin["decoded_bytes"]+prior_pin["bytes"]+prior_pin["decoded_bytes"]+len(canon(selected_contacts))+fragment_feature_bytes+component_expected_bytes+physical_code_bytes
    phys_raw=physical_pins["land"]["outer_bytes"]+physical_pins["lakes"]["bytes"]
    phys_dec=physical_pins["land"]["decoded_bytes"]+physical_pins["lakes"]["decoded_bytes"]
    phys_phase=phys_raw+phys_dec+physical_pins["land"]["intermediate_bytes"]+component_expected_bytes+physical_code_bytes+physical_result_bytes+old_physical_pin["bytes"]+old_physical_pin["decoded_bytes"]
    for name,size in (("complete-components",component_phase),("complete-fragments",fragment_phase),("complete-contacts",contact_phase),("complete-physical-inputs",phys_phase)):
        if size>PHASE_LIMIT: raise ValueError(f"{name} semantic phase exceeds 256 MiB: {size}")
    summary={"status":"authenticated bounded evidence reproduction; geography adjudication not performed",
      "issue":1389,"run_id":args.run_id,"started_utc":started,"contract_sha256":lock["issue_body_sha256"],
      "worker_visible_python":sys.version.split()[0],"families":family_records,"total_audited_raw_bytes":raw_total,
      "execution_code":{"path":"research/geography/nordic-reproduction-integrity-1233-erratum/reproduce.py","bytes":len(pathlib.Path(__file__).read_bytes()),"sha256":sha(pathlib.Path(__file__).read_bytes())},
      "complete_inventory_family_bindings":{"inventory_pin":inventory_pin,"families":inventory_families},
      "authentication_controls":[helper_control],"exclusive_output_controls":output_controls,
      "total_audited_decoded_bytes":decoded_total,"source_products":source_products,"atlas_subject_feature_hashes_by_vintage":byid,
      "retained_comparison_pin":prior_pin,"retained_physical_pin":old_physical_pin,
      "retained_subject_rows":prior.get("subject_feature_comparisons",[]),
      "retained_component_rows":prior.get("component_inputs",{}).get("component_rows",[]),
      "complete_component_scan":{"feature_count_scanned":component_scanned,"exact_ids":sorted(component_features),"shards":component_receipts,
        "phase_bytes":component_phase,"phase_limit":PHASE_LIMIT,"roster_controls":physical_controls},
      "complete_component_features":[component_features[fid] for fid in lock["component_ids"]],
      "complete_fragment_features":[fragment_features[fid] for fid in sorted(fragment_features)],
      "complete_fragment_scan":{"feature_count_scanned":fragment_scanned,"referenced_ids":sorted(fragment_features),"feature_sha256":{fid:sha(canon(f)) for fid,f in sorted(fragment_features.items())},"shards":fragment_receipts,"phase_bytes":fragment_phase,"phase_limit":PHASE_LIMIT},
      "complete_contact_scan":{"feature_count_scanned":contact_count,"selected_rows":selected_contacts,"pin":contact_receipt,"phase_bytes":contact_phase,"phase_limit":PHASE_LIMIT},
      "source_and_atlas_comparisons":{"countries":source_results,"phase_accounting":source_phase_bytes,"subject_and_country_measurements_match_retained":True},
      "complete_subject_comparisons":[r for iso in ("NOR","SWE") for r in source_results[iso]["subject_feature_comparisons"]],
      "complete_source_subject_features":[f for iso in ("NOR","SWE") for f in source_results[iso]["source_subject_features"]],
      "complete_atlas_C_subject_features":[f for iso in ("NOR","SWE") for f in source_results[iso]["atlas_C_subject_features"]],
      "combined_complete_source_overlay":{"results":combined_overlays,"phase_bytes":combined_phase_bytes,"phase_limit":PHASE_LIMIT},
      "physical_reproduction":{"pins":physical_pins,"result":physical,"matches_retained_result":True,"phase_bytes":phys_phase,"phase_limit":PHASE_LIMIT},
      "measurement_negative_control":measurement_control,
      "retained_physical_results":old_physical.get("results",[]),
      "limits":["The new runner reproduces the complete component, fragment, contact, full national source, both Atlas-vintage subject, and physical diagnostic measurements in separately accounted phases.",
        "The consumed source products are simplified historical files; original licensing assertions remain registry claims.",
        "No source authority, present boundary, physical land/water, legal meaning, causation or regional approval is established."]}
    payload=canon(summary)
    atomic_new(base,out,base_id,out_id,"authentication-and-phase-accounting.json",payload)
    receipt={"complete":True,"run_id":args.run_id,"outputs":{"authentication-and-phase-accounting.json":{"bytes":len(payload),"sha256":sha(payload)}},"started_utc":started,"finished_utc":datetime.now(timezone.utc).isoformat()}
    receipt_bytes=canon(receipt)
    atomic_new(base,out,base_id,out_id,"receipt.json",receipt_bytes)
    print(json.dumps({"run_id":args.run_id,"output":str(out),"phase_count":len(family_records),"phase_max_bytes":max(x["phase_bytes"] for x in family_records.values()),"receipt_sha256":sha(receipt_bytes)},indent=2))

if __name__ == "__main__":
    main()
