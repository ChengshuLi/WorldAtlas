#!/usr/bin/env python3
"""Inspect the locally retained SoI ABDB metadata ZIP without retaining extracts."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

EXPECTED_BYTES = 38_879
EXPECTED_SHA256 = "1a14716b73f00fc8391f2708a7975c2f2c1ad4a4e91aafb6dce6546a039e9514"
EXPECTED_MEMBERS = {
    "DISTRICT BOUNDARY.xlsx",
    "STATE BOUNDARY.xlsx",
    "SUB DISTRICT BOUNDARY.xlsx",
    "VILLAGE BOUNDARY.xlsx",
}
PRODUCTS = {
    "DISTRICT BOUNDARY.xlsx": "SOI/ABDB/VECTOR/50000/2025/DISTRICT/INDIA",
    "SUB DISTRICT BOUNDARY.xlsx": "SOI/ABDB/VECTOR/50000/2025/SUBDISTRICT/INDIA",
}
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
FIELDS = {
    "identifier": "MD_Metadata . metadataIdentifier . MD_Identifier . code",
    "published": "MD_Metadata . dateInfo . CI_Date . date",
    "title": "MD_Metadata . identificationInfo . MD_DataIdentification . citation . CI_Citation . title",
    "temporal_extent": "MD_Metadata . identificationInfo . MD_DataIdentification . extent . EX_Extent . temporalElement . EX_TemporalExtent . extent",
    "edition": "MD_Metadata . identificationInfo . MD_DataIdentification . citation . CI_Citation . date[dateType=edition] . CI_Date . date",
    "scale_denominator": "MD_Metadata . identificationInfo . MD_DataIdentification . spatialResolution . MD_Resolution . equivalentScale . MD_RepresentativeFraction . denominator",
    "plotted_accuracy_text": "MD_Metadata . identificationInfo . MD_DataIdentification . levelOfDetail",
    "crs": "MD_Metadata . referenceSystemInfo . MD_ReferenceSystem . referenceSystemIdentifier . RS_Identifier . code (Horizontal)",
    "lineage_text": "MD_Metadata . resourceLineage . LI_Lineage . statement",
    "horizontal_rmse": "MD_Metadata . dataQualityInfo . DQ_DataQuality . report . DQ_AbsoluteExternalPositionalAccuracy . result . DQ_DescriptiveResult . statement",
    "access_constraints": "MD_Metadata . identificationInfo . MD_DataIdentification . resourceConstraints . MD_LegalConstraints . accessConstraints (MD_RestrictionCode)",
    "use_constraints": "MD_Metadata . identificationInfo . MD_DataIdentification . resourceConstraints . MD_LegalConstraints . useConstraints (MD_RestrictionCode)",
    "other_constraints": "MD_Metadata . identificationInfo . MD_DataIdentification . resourceConstraints . MD_LegalConstraints . otherConstraints",
    "format": "MD_Metadata . distributionInfo . MD_Distribution . distributionFormat . MD_Format . name",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def xlsx_inventory(data: bytes) -> dict:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise ValueError(f"invalid XLSX member: {bad_member}")
        members = []
        for info in archive.infolist():
            decoded = archive.read(info.filename)
            members.append({
                "path": info.filename,
                "decoded_bytes": len(decoded),
                "sha256": digest(decoded),
            })
        return {"members": members, "decoded_bytes": sum(row["decoded_bytes"] for row in members)}


def workbook_fields(data: bytes) -> dict:
    with zipfile.ZipFile(io.BytesIO(data)) as workbook:
        shared_root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
        shared = [
            "".join(node.text or "" for node in item.findall(".//m:t", NS))
            for item in shared_root.findall("m:si", NS)
        ]
        sheet = ET.fromstring(workbook.read("xl/worksheets/sheet1.xml"))
        rows = {}
        for row in sheet.findall(".//m:sheetData/m:row", NS):
            cells = row.findall("m:c", NS)
            label_cell = next((cell for cell in cells if cell.get("r", "").startswith("A")), None)
            value_cell = next((cell for cell in cells if cell.get("r", "").startswith("B")), None)
            if label_cell is None or value_cell is None:
                continue
            label_value = label_cell.find("m:v", NS)
            value_value = value_cell.find("m:v", NS)
            if label_value is None or value_value is None:
                continue
            label = shared[int(label_value.text)] if label_cell.get("t") == "s" else label_value.text
            value = shared[int(value_value.text)] if value_cell.get("t") == "s" else value_value.text
            rows[label] = value
        extracted = {name: rows.get(label) for name, label in FIELDS.items()}
        if extracted["identifier"] is None:
            raise ValueError("metadata identifier missing")
        plotted = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*m", extracted.pop("plotted_accuracy_text") or "")
        extracted["plotted_accuracy_m"] = float(plotted.group(1)) if plotted else None
        extracted["lineage_present"] = bool(extracted.pop("lineage_text"))
        extracted["other_constraints_present"] = bool(extracted.pop("other_constraints"))
        return extracted


def inspect(path: Path, root: Path) -> dict:
    data = path.read_bytes()
    actual_hash = digest(data)
    positive_checks = {
        "exact_encoded_length": len(data) == EXPECTED_BYTES,
        "exact_encoded_sha256": actual_hash == EXPECTED_SHA256,
    }
    if not all(positive_checks.values()):
        raise ValueError(f"metadata source bytes differ from recorded retrieval: {positive_checks}")

    with zipfile.ZipFile(io.BytesIO(data)) as outer:
        bad_member = outer.testzip()
        if bad_member is not None:
            raise ValueError(f"invalid outer ZIP member: {bad_member}")
        infos = outer.infolist()
        names = {info.filename for info in infos}
        if names != EXPECTED_MEMBERS:
            raise ValueError(f"unexpected metadata inventory: {sorted(names)}")
        members = []
        products = {}
        nested_total = 0
        for info in sorted(infos, key=lambda item: item.filename):
            encoded = outer.read(info.filename)
            nested = xlsx_inventory(encoded)
            row = {
                "path": info.filename,
                "outer_compressed_bytes": info.compress_size,
                "outer_decoded_bytes": len(encoded),
                "sha256": digest(encoded),
                "xlsx_internal_member_count": len(nested["members"]),
                "xlsx_internal_decoded_bytes": nested["decoded_bytes"],
                "xlsx_internal_members": nested["members"],
            }
            members.append(row)
            nested_total += nested["decoded_bytes"]
            if info.filename in PRODUCTS:
                profile = workbook_fields(encoded)
                if profile["identifier"] != PRODUCTS[info.filename]:
                    raise ValueError(f"wrong product identifier in {info.filename}")
                profile["lineage_summary"] = "Metadata describes SoI 1:50,000-scale source material and a verification step; original source text omitted."
                products[info.filename] = profile

    # The source page's license/reuse status is not inferred by this byte test.
    mutated = bytearray(data)
    mutated[-1] ^= 1
    mutation_rejected = digest(mutated) != EXPECTED_SHA256
    truncation_rejected = len(data[:-1]) != EXPECTED_BYTES or digest(data[:-1]) != EXPECTED_SHA256
    if not mutation_rejected or not truncation_rejected:
        raise ValueError("negative controls failed to reject altered or incomplete bytes")

    execution = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    script_path = Path(__file__).resolve()
    return {
        "version": 1,
        "retrieved_on": "2026-10-06",
        "execution_commit": execution,
        "execution_code_sha256": digest(script_path.read_bytes()),
        "archive": {
            "official_url": "https://surveyofindia.gov.in/documents/Metadata_ABDB.zip",
            "encoded_bytes": len(data),
            "sha256": actual_hash,
            "outer_decoded_member_bytes": sum(row["outer_decoded_bytes"] for row in members),
            "nested_xlsx_decoded_bytes": nested_total,
            "all_inflation_layers_decoded_bytes": sum(row["outer_decoded_bytes"] for row in members) + nested_total,
            "members": members,
        },
        "product_metadata": products,
        "controls": {
            "positive": {
                "kind": "positive-control",
                "outcome": "passed",
                "checks": positive_checks,
                "outer_zip_crc_and_inventory": "passed",
                "nested_xlsx_crc": "passed",
                "district_and_subdistrict_product_ids": "passed",
            },
            "negative": {
                "kind": "negative-control",
                "outcome": "passed",
                "mutated_last_byte_rejected": mutation_rejected,
                "one_byte_truncation_rejected": truncation_rejected,
            },
        },
        "limits": [
            "This inspected the metadata ZIP only; the 202,524,438-byte RAR was not completely acquired or verified.",
            "The metadata ZIP is kept locally and is not distributed with the packet because its reuse terms remain unresolved.",
            "No SoI feature membership, per-subject name/code crosswalk, geometry or boundary comparison was verified.",
            "The byte controls do not establish legal permission to redistribute source bytes.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(json.dumps(inspect(args.archive, args.repo), sort_keys=True, indent=2) + "\n", end="")


if __name__ == "__main__":
    main()
