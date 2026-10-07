# Reproduction development record

The following safe outputs were created while refining the completeness validator. Their identical pair hashes and runner hashes are preserved here; redundant full reports are omitted from this PR. The final authoritative pair alone is retained in full under `runs/2026-10-07/final-v4/`.

| Iteration | Report SHA-256 (both runs) | Runner SHA-256 | Refinement |
|---|---|---|---|
| Initial | `e9984945e324a6b1be6640fd8fa35884c7feb86c1719f12f179d8b08189efee0` | `3291f8352969a80497d7de7c9d38f882c6001d61cd9912018cfad12d0a36f6bc` | All cases rejected, but some failures (including overlap) hit a generic count guard first. |
| Harness v1 | `9631cf5bd9f28e3a54a0b1145a53447835902166e7cf513735e793aff1e3587e` | `8355bc6ba1bc5ae8e5bad3b7fd9c7b14556697f76086d950795c2bcf27241f92` | Failure ordering and same-count overlap fixture corrected; predecessor omission authenticated. |
| Harness v2 | `956526578ef2080be41a361858743e5c8190ce75d95fde942567dd9d2aba04ce` | `f277a1784e7e9c4d0c45469b77ff56c65d4df4642719eeb56a57bf0ec133a06c` | Added verification that all four pinned v9/v10 comparison files retain the accepted common hash. |
| Harness v3 | `b479199523cb7d8fb0a6d3cdb614da9f56fe79b4711f427313b93ef71d348902` | `9e7cb23acfcb6d9bae661b01e944a444ccfef6e99b84d70bff1d2a8b83709fdd` | Added exact 23-record metadata and one-to-one parent-context checks. |

The final v4 run additionally binds all those conditions in the retained evidence manifest and `lineage-control.json`. The first iterations were generated only in this new owned prefix; no predecessor source, report, pin or worker file was edited.
