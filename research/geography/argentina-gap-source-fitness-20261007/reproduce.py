#!/usr/bin/env python3
"""Bounded source-fitness extraction from the immutable 2026-10-07 baseline."""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[3]
BASELINE = "6a47b43025d963daf80915c6d219c75ebcc8cd91"
OWNED = "research/geography/argentina-gap-source-fitness-20261007"
FAMILY = "gap-source-batch:af41d8136269b78548021a84"
CONTACTS = [
    "gb:ARG:ADM2:61730980B13025573352502",
    "gb:ARG:ADM2:61730980B44606052944654",
    "gb:ARG:ADM2:61730980B51096129050346",
    "gb:ARG:ADM2:61730980B99310691740446",
]
COMPONENTS = [
    "physical-component:005bc7c364b9d663c7bde452916a80ca6cc4d06411ffbd8d5cd9bd621c84dbf5",
    "physical-component:147ddc6aed102d3f2c5e362d8a37a159db9d185a652feb75afe5f8e5b57918d0",
    "physical-component:1635eecba78b0a2f8477bdd03d603cea93c4ff2d9c68f1a963bd44934790695a",
    "physical-component:7bd46b9a5ab80cc933fa4de4f0564dc34ee1edf4eef0ed500b875c409ea6df04",
    "physical-component:91bd8745a426b126855fef4cf183a85e8329b7943cc1c89b02898038c0dceea0",
    "physical-component:b960e6adda1b56e25b52f8a501b7f6fdc86a461b71e94ec9aaec057cee45b27e",
    "physical-component:c86d0a6bd3706c3dae7df4b91bc50af6ecd7f07e9bd886b471064c9c84beecdf",
]
PIN_FILES = {
    "evidence_immutable_helper": "scripts/evidence/immutable.py",
    "global_routing_report": "coordination/engineering/global-actionability-routing-20261007/results/report.json",
    "global_routing_evidence_policy": "coordination/engineering/global-actionability-routing-20261007/evidence-quality.json",
    "routed_family_slice_009": "coordination/engineering/global-actionability-routing-20261007/results/families-009.bin.gz",
    "land_source_fitness_slice_000": "coordination/engineering/global-actionability-routing-20261007/results/land-source-fitness-000.bin.gz",
    "physical_component_inputs_005": "coordination/engineering/global-source-comparisons-a-20261006/global-source-comparisons-a-000-20261006/scientific/components-005.json.gz",
    "physical_component_inputs_007": "coordination/engineering/global-source-comparisons-a-20261006/global-source-comparisons-a-000-20261006/scientific/components-007.json.gz",
    "physical_component_inputs_008": "coordination/engineering/global-source-comparisons-a-20261006/global-source-comparisons-a-000-20261006/scientific/components-008.json.gz",
    "current_contact_partition": "data/geography/part-0.json",
    "current_source_registry": "data/administrative-sources.json",
    "baseline_recipe": "scripts/administrative.py",
    "baseline_location_policy": "data/location-policy.json",
    "original_source_catalogue": "coordination/engineering/original-geography-source-corpus-20261006/catalogue.json",
    "consumed_simplified_ARG_ADM2": "coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-ARG-ADM2-000.bin.gz",
    "prior_ARG_unsimplified_source_archive": "data/regional-review/regional-review-7cf674a63057d43f/source/geoBoundaries-ARG/geoBoundaries-ARG-ADM2.geojson.gz",
    "prior_ARG_source_metadata": "data/regional-review/regional-review-7cf674a63057d43f/source/geoBoundaries-ARG/geoBoundaries-ARG-ADM2-metaData.json",
    "prior_442_source_inventory": "data/regional-review/regional-review-fd433005036fe22b/source-inventory.json",
    "prior_442_geometry_comparisons": "data/regional-review/regional-review-fd433005036fe22b/geometry-comparisons.jsonl",
    "prior_442_issue_snapshot": "data/regional-review/regional-review-fd433005036fe22b/issue-snapshot.json",
    "prior_442_artifact_checksums": "data/regional-review/regional-review-fd433005036fe22b/artifact-checksums.json",
    "prior_Georef_crosswalk": "data/regional-review/regional-review-fd433005036fe22b/vintages/2026-10-05-georef-cc-by4/departamentos.geojson",
}
# Exact whole-file values in the ready #1418 issue contract.
PINS = {
    "evidence_immutable_helper": "a3667cecd88b2862e61a3ce72778e179535d92fbf19b5cd7c5b112722926da46",
    "global_routing_report": "2bf401f76aabc30cb9f0120aba958545146ebf37e304d8817d15eed800fa5265",
    "global_routing_evidence_policy": "1551d9a51aa7c2407f4ab9733bf2f515aed865670579eb2dbd34d4a405faf3b9",
    "routed_family_slice_009": "4621441988498fe2c05bfe6f036bf8dd9cfbc8472c5b8a65bf91d3a424f626da",
    "land_source_fitness_slice_000": "98382c95655a927c4075e7de5c8aa5204980340d001cfb28d9993823cc3d8476",
    "physical_component_inputs_005": "9dad08bf51b832b1c8e1868f3571d58ec52633cf7e9b43016f681aad398f20d1",
    "physical_component_inputs_007": "89b1bdf8472d92dbad5dd65ba0d00dcbf76f808af844b7e9b78cb5fc318f22d5",
    "physical_component_inputs_008": "f4ecb53c8f78853d77bbc05ab184201fbf1a7087a38ae793353ed68406028a1c",
    "current_contact_partition": "bcad5408720e0f50165e794636fd44e02913e5e4649d73c8aa422b94562d32f3",
    "current_source_registry": "ed0051d2956271c72f8917e7da0c6f53e5dfb595bee5920cac489a65a747d633",
    "baseline_recipe": "d9df8285f1c270856a8e79b95636cf4b8d8496f48b30348a1e4d6d20619b2f22",
    "baseline_location_policy": "efab4528fd4b7b180815ef82de93480f490ef8fa48ad9ef32d1f9d76a64b7fb9",
    "original_source_catalogue": "d3da799558be1fcbe7f3ea90ba7033d312a65690984983cb008f2d72e32765f9",
    "consumed_simplified_ARG_ADM2": "9b033d8e86946b8f14d9491ec51098e3c5c0e59785707058966d1fc77521546d",
    "prior_ARG_unsimplified_source_archive": "aaf34413713c3b75175d04b6b7cafa4910ebdca762d2637a6547024466e3e07e",
    "prior_ARG_source_metadata": "17452b82df4498c1b29a4489bd78709cef922b453579b1a47010dfd2524a7ce2",
    "prior_442_source_inventory": "2a794c330534b74bedf5c77dc813386fd5fb1195649ca23ded3bd99b53f12007",
    "prior_442_geometry_comparisons": "9e55c66fc509f35aaf618d5fd1c6ac1338bbeabdc741a32043d4be9d35e12a1c",
    "prior_442_issue_snapshot": "8a86cb2c66c9f29171abb2dd26e74e7af247b3de3a9f61b967ed277831ec3dde",
    "prior_442_artifact_checksums": "8ee5199d16992007cbbb5d9b59875734114b04f705c80e21454475bffe56aa70",
    "prior_Georef_crosswalk": "31afdfe5983b6d7648eba1eafc7a5a8fe3c591abdca4b17c311c08c75d361e92",
}
MAX_FILE = 32 * 1024 * 1024
MAX_PHASE = 256 * 1024 * 1024
helper_bytes = subprocess.check_output(["git", "-C", str(ROOT), "show", BASELINE + ":scripts/evidence/immutable.py"])
helper_sha256 = hashlib.sha256(helper_bytes).hexdigest()
if helper_sha256 != PINS["evidence_immutable_helper"]:
    raise ValueError("shared evidence helper differs from the issue-pinned baseline")
sys.path.insert(0, str(ROOT / "scripts"))
# Execute the exact bytes read from the issue-pinned baseline. Importing the
# materialized checkout module here would only authenticate its Git counterpart,
# not prove that these are the bytes Python actually executes.
_immutable = types.ModuleType("worldatlas_pinned_immutable")
_immutable.__file__ = "git:" + BASELINE + ":scripts/evidence/immutable.py"
exec(compile(helper_bytes, _immutable.__file__, "exec"), _immutable.__dict__)
Baseline = _immutable.Baseline
NewVintage = _immutable.NewVintage
canonical_json = _immutable.canonical_json
descriptor = _immutable.descriptor
sha256 = _immutable.sha256
write_new_vintage = _immutable.write_new_vintage
EXECUTION_BINDING = {
    "baseline_commit": BASELINE,
    "helper_path": "scripts/evidence/immutable.py",
    "helper_sha256": helper_sha256,
    "helper_execution": "compile+exec captured git-show bytes; no checkout import",
    "runner_path": str(Path(__file__).resolve().relative_to(ROOT)),
    "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "python_version": sys.version,
    "python_executable": sys.executable,
}
BASELINE_READER = None


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], stderr=subprocess.PIPE)


def read_baseline(name, override=None):
    if name not in PIN_FILES.values():
        raise ValueError("unlisted baseline input: " + name)
    if BASELINE_READER is None:
        raise ValueError("immutable baseline reader has not been initialized")
    expected = BASELINE_READER.pinned_bytes(name)
    if override is not None:
        raw = override
    elif name == PIN_FILES["baseline_location_policy"]:
        # This immutable source file may be absent from a sparse checkout. Read
        # its pinned Git blob directly; no working-tree substitute is accepted.
        raw = BASELINE_READER.pinned_bytes(name)
    else:
        raw = BASELINE_READER.materialized_bytes(name)
    if len(raw) > MAX_FILE or sha(raw) != sha(expected):
        raise ValueError("whole-file SHA-256 mismatch: " + name)
    return raw


def load_case(family_override=None):
    global BASELINE_READER
    if set(PINS) != set(PIN_FILES):
        raise ValueError("issue pin inventory and bound paths differ")
    if sum(1 for _ in PINS) == 0:
        raise ValueError("empty baseline pin set")
    descriptors = []
    for key, path in PIN_FILES.items():
        raw = git("show", BASELINE + ":" + path)
        if sha(raw) != PINS[key] or len(raw) > MAX_FILE:
            raise ValueError("baseline pin mismatch or file cap exceeded: " + key)
        descriptors.append(descriptor(path, raw))
    BASELINE_READER = Baseline(ROOT, BASELINE, descriptors, max_phase_bytes=MAX_PHASE)
    inputs = {}
    consumed = 0
    for key, path in PIN_FILES.items():
        raw = read_baseline(path, family_override if key == "routed_family_slice_009" else None)
        consumed += len(raw)
        if consumed > MAX_PHASE:
            raise ValueError("phase exceeds 256 MiB cap")
        inputs[path] = raw
    return inputs


def build_report(inputs):
    def j(path):
        raw = inputs[path]
        if path.endswith(".gz"):
            raw = gzip.decompress(raw)
            if len(raw) > MAX_FILE:
                raise ValueError("decoded input exceeds 32 MiB: " + path)
        return json.loads(raw)

    def gz_json(path):
        raw = gzip.decompress(inputs[path])
        if len(raw) > MAX_FILE:
            raise ValueError("decoded input exceeds 32 MiB: " + path)
        return raw, json.loads(raw)

    family_path = PIN_FILES["routed_family_slice_009"]
    family_raw = gzip.decompress(inputs[family_path])
    if len(family_raw) > MAX_FILE:
        raise ValueError("decoded family shard exceeds 32 MiB cap")
    needle = FAMILY.encode()
    pos = family_raw.find(needle)
    if pos < 0:
        raise ValueError("family row absent from routed slice")
    start = family_raw.rfind(b"\n", 0, pos) + 1
    end = family_raw.find(b"\n", pos)
    family_line = family_raw[start:end]
    family = json.loads(family_line)
    if family.get("id") != FAMILY:
        raise ValueError("wrong family row selected")
    if family.get("complete_component_ids") != COMPONENTS or family.get("component_count") != 7:
        raise ValueError("complete family roster mismatch")
    roster_sha = sha((json.dumps(COMPONENTS, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode())
    if roster_sha != "b2b8155d09bfa4e86a51b8ed6617927790e9c666c9294f96fcc9a7453b87dbda":
        raise ValueError("component roster digest mismatch")

    component_rows = []
    for suffix in ("005", "007", "008"):
        p = PIN_FILES["physical_component_inputs_" + suffix]
        _, shard = gz_json(p)
        component_rows.extend(row for row in shard if row.get("family") == FAMILY)
    by_id = {row["component"]: row for row in component_rows}
    if len(component_rows) != 7 or list(x for x in COMPONENTS if x in by_id) != COMPONENTS:
        raise ValueError("component rows are incomplete, duplicated, or reordered")

    land_rows = j(PIN_FILES["land_source_fitness_slice_000"])
    land_family_rows = [row for row in land_rows if row.get("family") == FAMILY]
    expected_land = ["physical-component:7bd46b9a5ab80cc933fa4de4f0564dc34ee1edf4eef0ed500b875c409ea6df04"]
    if [row.get("component") for row in land_family_rows] != expected_land:
        raise ValueError("land/source fitness row differs from exact one-component family result")

    contact_partition = j(PIN_FILES["current_contact_partition"])
    features = contact_partition.get("features", [])
    contact_features = {f.get("id", f.get("properties", {}).get("id")): f for f in features
                        if f.get("id", f.get("properties", {}).get("id")) in CONTACTS}
    if set(contact_features) != set(CONTACTS):
        raise ValueError("current contact subjects are incomplete")

    catalogue = j(PIN_FILES["original_source_catalogue"])
    product = next(p for p in catalogue["products"] if p["key"] == "gb:ARG:ADM2")
    policy = j(PIN_FILES["baseline_location_policy"])
    arg_policy = policy["countries"]["ARG"]
    recipe = inputs[PIN_FILES["baseline_recipe"]].decode("utf-8")
    transform = "rule['source_url'].replace('.geojson','_simplified.geojson')"
    if transform not in recipe:
        raise ValueError("baseline recipe lacks the pinned simplification transform")
    selected_url = arg_policy["source_url"]
    consumed_url = selected_url.replace(".geojson", "_simplified.geojson")
    if consumed_url != product["recorded_consumed_url"]:
        raise ValueError("pinned Argentina policy and recipe do not resolve to the consumed catalogue URL")
    source_path = PIN_FILES["consumed_simplified_ARG_ADM2"]
    source_bytes = gzip.decompress(inputs[source_path])
    if len(source_bytes) != product["original_bytes"] or sha(source_bytes) != product["original_sha256"]:
        raise ValueError("consumed simplified product bytes disagree with catalogue")
    if len(source_bytes) > MAX_FILE:
        raise ValueError("decoded source product exceeds 32 MiB cap")
    source = json.loads(source_bytes)
    if len(source.get("features", [])) != product["feature_count"] or len(source["features"]) != 525:
        raise ValueError("consumed simplified feature count mismatch")
    source_contacts = {}
    for feature in source["features"]:
        props = feature.get("properties", {})
        shape = props.get("shapeID")
        for subject in CONTACTS:
            if shape == subject.rsplit(":", 1)[1]:
                source_contacts[subject] = {"shapeID": shape, "shapeName": props.get("shapeName"),
                                            "shapeParent": props.get("shapeParent"),
                                            "canonical_feature_sha256": sha(json.dumps(feature, sort_keys=True,
                                                ensure_ascii=False, separators=(",", ":")).encode())}
    if set(source_contacts) != set(CONTACTS):
        raise ValueError("simplified source contact identities incomplete")
    for subject in CONTACTS:
        current = contact_features[subject].get("properties", {})
        if current.get("name") != source_contacts[subject]["shapeName"]:
            raise ValueError("source/current contact name mismatch: " + subject)
        source_contacts[subject]["current_name"] = current.get("name")
        source_contacts[subject]["current_parent_id"] = current.get("parent_id")
    if source.get("crs", {}).get("properties", {}).get("name") != "urn:ogc:def:crs:OGC:1.3:CRS84":
        raise ValueError("unexpected source CRS")

    consumed_shapes = set()
    for row in (by_id[i] for i in COMPONENTS):
        for intersection in row.get("feature_intersections", []):
            shape_id = intersection.get("binding", {}).get("shapeID")
            if shape_id:
                consumed_shapes.add(shape_id)
    source_features = {}
    for feature in source["features"]:
        props = feature.get("properties", {})
        if props.get("shapeID") in consumed_shapes:
            source_features[props["shapeID"]] = {
                "shapeID": props["shapeID"], "shapeName": props.get("shapeName"),
                "shapeParent": props.get("shapeParent"),
            }
    if set(source_features) != consumed_shapes or len(consumed_shapes) != 6:
        raise ValueError("all six admin source identities in component rows must resolve")

    metadata = j(PIN_FILES["prior_ARG_source_metadata"])
    registry = j(PIN_FILES["current_source_registry"])
    registry_entry = registry.get("gb:ARG:ADM2")
    unsimplified = j(PIN_FILES["prior_442_source_inventory"])
    georef_issue = j(PIN_FILES["prior_442_issue_snapshot"])
    georef_source = j(PIN_FILES["prior_Georef_crosswalk"])
    georef_by_shape = {}
    for shape_id, source_feature in sorted(source_features.items()):
        matches = [f.get("properties", {}) for f in georef_source.get("features", [])
                   if f.get("properties", {}).get("nombre") == source_feature["shapeName"]]
        if len(matches) != 1 or matches[0].get("provincia", {}).get("nombre") != "Buenos Aires":
            raise ValueError("Georef exact-name comparator row is absent, ambiguous, or outside Buenos Aires: " + shape_id)
        props = matches[0]
        georef_by_shape[shape_id] = {
            "source_shapeName": source_feature["shapeName"],
            "georef_id": props.get("id"), "nombre": props.get("nombre"),
            "nombre_completo": props.get("nombre_completo"),
            "provincia": props.get("provincia"), "fuente": props.get("fuente"),
            "categoria": props.get("categoria"),
            "match_basis": "exact name and Buenos Aires province only; no geometry identity asserted",
        }
    # Preserve complete original feature-intersection and neighbor rows. No geometry
    # libraries are loaded: this is source identity/record reconciliation only.
    report = {
        "version": 1,
        "baseline_commit": BASELINE,
        "family_id": FAMILY,
        "operational_batch": family.get("operational_batch"),
        "family_scope": {"component_ids": COMPONENTS, "component_ids_sha256": roster_sha,
                         "component_count": len(COMPONENTS)},
        "contacts": CONTACTS,
        "contact_names_and_current_features": contact_features,
        "positive_length_neighbors": family.get("complete_positive_length_neighbor_ids"),
        "family_record": family,
        "complete_component_source_rows_in_family_order": [by_id[i] for i in COMPONENTS],
        "recorded_land_source_fitness_rows": land_family_rows,
        "all_component_admin_source_features_by_shapeID": source_features,
        "source_product": {
            "catalogue_record": product,
            "exact_source_url": product["recorded_consumed_url"],
            "retrieval_timestamp": "not recorded in pinned catalogue; corpus path identifies 2026-10-06 collection campaign",
            "represented_year_claim": product["source_represented_year_claim"],
            "native_crs": source["crs"],
            "axis_order": "longitude, latitude (CRS84)",
            "feature_count": len(source["features"]),
            "decoded_bytes": len(source_bytes),
            "decoded_sha256": sha(source_bytes),
            "contacts_by_shapeID": source_contacts,
            "component_admin_source_feature_count": len(source_features),
            "source_metadata": metadata,
            "registry_entry": registry_entry,
            "terms": "CC BY 3.0 IGO stated by retained product metadata/catalogue; this assessment does not extend, resolve, or independently approve upstream permissions",
            "locator_discrepancy": "routing row records unsimplified locator; this exact consumed baseline product is the simplified release; byte identities are not equated",
        },
        "prior_assessments": {
            "issue_442_source_inventory": unsimplified,
            "unsimplified_source_admission": {
                "encoded_archive_descriptor": descriptor(PIN_FILES["prior_ARG_unsimplified_source_archive"],
                                                          inputs[PIN_FILES["prior_ARG_unsimplified_source_archive"]]),
                "decoded_identity_as_recorded_in_pinned_442_inventory": {
                    "bytes": next(x["retrieved_file_bytes"] for x in unsimplified["sources"] if x["id"] == "gb:ARG:ADM2"),
                    "sha256": next(x["retrieved_file_sha256"] for x in unsimplified["sources"] if x["id"] == "gb:ARG:ADM2"),
                },
                "decoded_input_admission": "refused; recorded decoded size exceeds the 32 MiB per-file limit; no decompression or geometry admission performed",
            },
            "source_locator_resolution": {
                "baseline_location_policy_path": PIN_FILES["baseline_location_policy"],
                "baseline_location_policy_sha256": PINS["baseline_location_policy"],
                "selected_unsimplified_url": selected_url,
                "baseline_recipe_transform": transform,
                "resolved_simplified_url": consumed_url,
                "catalogue_url_matches": True,
            },
            "georef_prior_issue_snapshot": georef_issue,
            "georef_crosswalk_feature_count": len(georef_source.get("features", [])),
            "georef_crosswalk_exact_name_matches_for_all_component_admin_rows": georef_by_shape,
            "limits": ["#442 assessed 241 Argentina Northeast locations; contact reuse does not imply component/family overlap",
                       "#442 unsimplified source response is 69,702,323 bytes and advertised count differs from observed count; decoded payload exceeds current 32 MiB cap and was not opened here",
                       "#960 Georef comparator captured 2026-10-05; layer vintage and reuse terms remain unconfirmed; not an independent legal authority"]
        },
        "assessment": {
            "source_identity": "The consumed simplified product contains exact shapeIDs and names for four current contacts; all seven component source rows are preserved below.",
            "scope": "Source-relative evidence only. No exact dry-land, legal-boundary, authority, effective-date, ownership, physical-completeness, or source-cause approval.",
            "unknowns": ["boundary length", "physical authority", "cause", "effective date", "lineage", "surface/land-water status", "physical completeness", "legal ownership", "product-specific retrieval timestamp"]
        },
        "input_descriptors": {path: {"bytes": len(raw), "sha256": sha(raw)} for path, raw in sorted(inputs.items())},
        "execution_binding": EXECUTION_BINDING,
    }
    return report


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode()


def write_vintage(name, report, mutation_control):
    if not re.fullmatch(r"argentina-run-[1-4]", name):
        raise ValueError("run name must be argentina-run-1 through argentina-run-4")
    root = ROOT / OWNED / "vintages" / name
    outputs = {
        "source-fit.json": report,
        "component-source-rows.json.gz": report["complete_component_source_rows_in_family_order"],
        "family-record.json": report["family_record"],
        "mutation-control.json": mutation_control,
        "positive-control.json": {
            "method_id": "argentina-source-extract", "kind": "positive-control", "outcome": "passed",
            "expected_family_id": FAMILY, "observed_family_id": report["family_id"],
            "expected_component_ids": COMPONENTS,
            "observed_component_ids": report["family_scope"]["component_ids"],
            "contact_count": len(report["contacts"]), "admin_source_feature_count": len(report["all_component_admin_source_features_by_shapeID"]),
        },
    }
    (ROOT / OWNED / "vintages").mkdir(parents=True, exist_ok=True)
    vintage = NewVintage(BASELINE_READER, OWNED + "/", name, list(outputs))
    artifacts = vintage.publish(outputs)
    return {"path": str(vintage.root.relative_to(ROOT)), "artifacts": artifacts}


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run")
    group.add_argument("--finalize-reproducibility", action="store_true")
    parser.add_argument("--execution-log")
    args = parser.parse_args()
    inputs = load_case()
    if args.finalize_reproducibility:
        if not args.execution_log:
            raise ValueError("actual process receipt required for reproducibility finalization")
        paths = [ROOT / OWNED / "vintages" / f"argentina-run-{n}" / "source-fit.json" for n in (1, 2)]
        reports = [p.read_bytes() for p in paths]
        if reports[0] != reports[1]:
            raise ValueError("two complete source-fit reports differ")
        result = {"method_id": "argentina-source-extract", "kind": "reproducibility", "outcome": "passed",
                  "run_one_sha256": sha(reports[0]), "run_two_sha256": sha(reports[1]),
                  "run_paths": [str(p.relative_to(ROOT)) for p in paths],
                  "equal_bytes": True}
        execution = json.loads(Path(args.execution_log).read_text(encoding="utf-8"))
        if execution.get("outcome") != "passed" or len(execution.get("processes", [])) != 2:
            raise ValueError("require two successful recorded extraction processes")
        vintage = NewVintage(BASELINE_READER, OWNED + "/", "argentina-repro-check-v2",
                             ["reproducibility.json", "execution-receipt.json"])
        record = vintage.publish({"reproducibility.json": result, "execution-receipt.json": execution})
        print(json.dumps({"reproducibility": result, "published": record}, indent=2, sort_keys=True))
        return
    report = build_report(inputs)
    # Exercise the actual admitted-input path with a corrupted family shard. The
    # mutated bytes are rejected before compute/write; no baseline or output file changes.
    family_name = PIN_FILES["routed_family_slice_009"]
    raw = inputs[family_name]
    marker = COMPONENTS[0].encode()
    decoded = gzip.decompress(raw)
    changed_decoded = decoded.replace(marker, marker + b"-tampered", 1)
    changed = gzip.compress(changed_decoded, mtime=0)
    if changed == raw:
        raise ValueError("negative control failed to mutate the input")
    rejected = False
    try:
        read_baseline(family_name, changed)
    except ValueError as error:
        rejected = "whole-file SHA-256 mismatch" in str(error)
        rejection = str(error)
    if not rejected:
        raise ValueError("mutated full-family input was not rejected by actual reader")
    mutation_control = {"method_id": "argentina-source-extract", "kind": "negative-control", "outcome": "passed",
                        "control": "changed one component identity in complete family shard",
                        "changed_input_sha256": sha(changed), "rejection": rejection,
                        "observed_before_compute_or_write": True}
    result = write_vintage(args.run, report, mutation_control)
    result["mutation_control"] = mutation_control
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
