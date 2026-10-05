# West Africa Benin and Burkina Faso source review (#467)

Research packet for the exact 224-member issue scope: 77 Benin communes and 147 of 351 Burkina Faso communes. It reviews source role, vintage, license, source-ID/name joins, parent relationships, geometry provenance, neighboring administrative granularity, and limits. The issue snapshot preserves the exact scope and original machine contract.

## Findings

- Individual assessment is provided for all 224 locations and all 30 scoped parent groups. Location counts are 189 `justified`, 35 `insufficient-evidence`, and 0 `correction-needed`. The four Benin parent display-name handoffs are separately recorded; they preserve IDs and memberships.
- Benin 2007 source role is Commune (ADM2); Burkina Faso's 2007 source role is Commune (ADM3), established from the exact Stanford/UT Austin catalog record and official INSD tables, not inferred from ADM codes. Both source collections state Public Domain. All scoped source IDs and names match.
- The 33 Benin children with under-95% overlap to the later 2012 parent layer need a same-vintage official parent crosswalk. Niangologo and Kando have under-95% source/current overlap; the recorded topology reconciliation does not reproduce their exact transformation provenance. These are uncertainty findings, not proven boundary errors.
- Neighboring country comparison uses eight local administrative source cohorts. It is contextual only: tier labels, counts, and area distributions do not certify semantic equivalence or source completeness.
- No independent source inspected establishes exhaustive coastline/islet coverage. This packet does not approve the regional envelope, certify Benin or Burkina Faso as a whole, or permit imports.

## Reproduction

Use Python 3.12 with the exact dependency pins in the repository `requirements.txt` and the shared `scripts/evidence/geometry.py` helper. Example in an environment with these packages installed:

```sh
PYTHONPATH=scripts/evidence:scripts python3 data/regional-review/regional-review-5d48dd1f18c0b48e/reproduce_scope.py
PYTHONPATH=scripts/evidence:scripts python3 data/regional-review/regional-review-5d48dd1f18c0b48e/audit_geography.py
PYTHONPATH=scripts/evidence:scripts python3 data/regional-review/regional-review-5d48dd1f18c0b48e/audit_neighbor_granularity.py
PYTHONPATH=scripts/evidence:scripts python3 data/regional-review/regional-review-5d48dd1f18c0b48e/build_assessments.py
PYTHONPATH=scripts/evidence:scripts python3 data/regional-review/regional-review-5d48dd1f18c0b48e/packet_controls.py
python3 data/regional-review/regional-review-5d48dd1f18c0b48e/build_evidence_manifest.py
node scripts/evidence-quality.mjs data/regional-review/regional-review-5d48dd1f18c0b48e/evidence-quality.json
```

The geography screen includes identical-polygon and disjoint-polygon controls. The neighboring-tier measurement has a known-area positive control and rejects out-of-range coordinates; the packet generator checks positive exact joins and rejects duplicate scope IDs. `reproducibility.json` records two complete replays. It uses the shared WGS84 straight-source-edge area helper and Shapely planar longitude/latitude overlays; results are diagnostic and not survey-grade boundary determinations. `source-research.md`, `scope-source-inventory.json`, retained source assets, and `evidence-quality.json` preserve citations, exact hashes, retrieval date, licenses, methods, and restoration instructions. Source metadata/reference layers and official pages are described separately; the official statistical PDFs that could not be retained must be restored from their cited URLs before repeating those table-level inspections.
