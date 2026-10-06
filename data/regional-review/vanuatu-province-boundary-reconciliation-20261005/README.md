# Vanuatu province boundary reconciliation — issue #912

**Research status: partial; all six subject classifications remain `insufficient-evidence`.** This packet identifies the six ADM1 subjects, reproduces source identity and geometric comparison screens, inventories consulted government references and pins their exact retrieval bytes. It does not approve any geography or certify the Vanuatu region.

## What the evidence supports

The DLA identifies six provinces and describes each in island-group terms. Its current area-council page enumerates 71 subordinate councils. The 2017 geoBoundaries OSM/Wambacher ADM1 cohort has six matching native IDs and names and is licensed ODbL 1.0. The matching 1,094,439-byte GeoJSON is already lawfully retained in the prior #454 packet; this packet references its exact hash and does not duplicate it. The upstream Git LFS object hash matches those retained bytes. The administrative registry's `63e187…` hash was generated from importer cache `.cache/VUT-ADM1.json`, which is not in the reviewed baseline; it is a different byte object, and its provenance cannot be independently reconciled from available pinned evidence.

## Findings by subject

| Province | Tier and broad group evidence | Boundary/completeness finding |
|---|---|---|
| Shefa | DLA names Shepherds, Epi and Efate; profile adds Emae, Tongoa, Tongariki/Buninga, Makira/Mataso, Emau and Moso/Lelepa. | `insufficient-evidence`: municipality exclusion and exact current legal linework are unresolved; profile-era and current council rosters differ. |
| Malampa | DLA/profile and current roster name Malekula, Ambrym and Paama. | `insufficient-evidence`: exact legal limits and small-island completeness are unproven. |
| Tafea | DLA/profile name Tanna, Aneityum, Futuna and Erromango; profile/current roster also names Aniwa. | `insufficient-evidence`: Lenakel municipality exclusion and exact legal limits are unresolved. |
| Sanma | DLA names Santo, Malo and Aore. | `insufficient-evidence`: Luganville municipality exclusion and exact legal limits are unresolved; Aore is not a named current area council. |
| Penama | DLA names Pentecost, Ambae and Maewo. | `insufficient-evidence`: exact legal limits and outer-island completeness are unproven. |
| Torba | DLA names Banks and Torres groups. | `insufficient-evidence`: exact legal limits and small-island completeness are unproven; profile-era council count differs from current roster. |

The `reproduction.json` overlap measures compare Atlas footprints only with the 2017 OSM-derived source using repository WGS84 straight-edge ellipsoidal geometry helpers. They are discrepancy screens, not correctness scores. No automated repair or acceptance threshold is applied.

## Authority, granularity and limits

The 2025 consolidated Decentralization Act places legal boundary authority in Orders: s3(1)(c) covers province-region boundaries, s4A covers subordinate area-council divisions, and s34 excludes municipalities from provincial government regions. The consulted official material did not yield the current boundary-defining Orders, amendment history, or precise legal linework. DLA's six provincial profiles are government-published maps and profiles, but their page asset modified labels do not establish map-data vintage; the profile text is older than the current DLA council roster. DUAP identifies Port Vila, Luganville and Lenakel as municipalities. It links a titled Port Vila planning map (2016–2030); we hash that PDF but do not interpret its cartography or legal effect. Exact legal municipality boundary geometry was not established here.

DLA's current list has 71 area councils; the separate brochure has a conflicting distribution and total. The 2018 OCHA/Pacific Community ADM2 service contains 66 features and its license metadata is blank. These are neighboring-tier references with differing apparent granularity; no unverified five-feature crosswalk is inferred. Neither source settles provincial lines or completeness. No redistribution license was located for the downloaded DLA PDFs; the packet records URL, SHA-256, byte size and facts only, and treats the originals as restoration-only.

## Engineering handoff

Obtain current province-defining Orders and amendments, subordinate Orders where needed to interpret current administrative rosters, and legal municipal boundary maps/orders for Port Vila, Luganville and Lenakel. Establish each source's effective date and lawful retention terms. Crosswalk every named island and municipality exclusion against all six subjects. If authoritative geometry shows differences, propose a separately reviewed coordinated correction across affected neighbors; do not alter core geography in this research packet.

## Reproduction

Run from repository root with bundled Python dependencies:

```sh
PYTHONPATH=scripts:scripts/evidence python3 data/regional-review/vanuatu-province-boundary-reconciliation-20261005/reproduce.py
```

The script reads only commit `a32ae163473a42ed28d7bedf7e9930414beb54f8`, checks explicit whole-file SHA-256/byte pins, verifies the exact six-subject index roster and native source ID/name controls, then computes the geometry screen with the shared helpers. It writes the candidate `reproduction.json`. Every subject remains unapproved and unresolved on exact boundaries/completeness.
