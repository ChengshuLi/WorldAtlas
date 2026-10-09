# Argentina ring-renderer integrity erratum

Research date: 2026-10-08 (America/Los_Angeles). This additive packet addresses only the exact 214-subject consumed-input and complete-output integrity defects found after PR #1132. The original #953/#1129 inputs, code, output vintage, identifiers and issue history are retained unchanged.

## Reproduction

From the repository root, run with Python 3 (standard library only; the exact runtime is recorded in the result vintage):

```sh
python3 research/geography/argentina-ring-validator-integrity-1132-erratum/guarded-renderer.py \
  --vintage argentina-ring-integrity-local-20261009-a1
```

The guarded entry point reads every historical input and the legacy runner from immutable merge `0f08ca8c451e71bb3b06cb5fb82988e92d3048ab`, verifies each whole-file hash and size against `input-pins.json`, and confirms the corresponding checked-out bytes before use. It captures those bytes once into private temporary files, then executes the unchanged pinned `corrected-renderer.py` CLI twice with the exact scope, source, table, and production categorizer. Both complete seven-product sets must match one another and the four pinned prior products. The packet independently reads the rendered table and verifies the unchanged summary row and all non-target detail cells, along with the 214 exact IDs, 213 corrected false flags, and Itatí's five rings. `run-summary.json` also binds the prior source-register's recorded full-object feature count and the source metadata's declared ADM2 count to their actual pinned JSON fields.

Before computation, the runner reserves the entire ten-file result inventory beneath this packet's fresh `vintages/<name>/` path using `scripts/evidence/immutable.py`'s `Baseline` and `NewVintage` safeguards. It rejects noncanonical input paths and existing files/directories, broken symlinks, symlinked ancestors, and escaped output paths. New files are installed exclusively; `publication.json` is installed only after every product has been flushed. A failed write leaves an unaccepted partial vintage without a publication receipt and must be assigned a new vintage name on retry.

Run the bounded adverse-path suite with:

```sh
python3 -m unittest discover -s research/geography/argentina-ring-validator-integrity-1132-erratum -p 'test_guarded_renderer.py'
```

## Source, vintage and limits

The retained input is the 2020 geoBoundaries Argentina ADM2 extract retrieved 2026-10-05 from upstream commit `9469f09`; its pinned metadata names Instituto Geográfico Nacional and UNHCR/OCHA ROLAC and declares CC BY 3.0 IGO. geoBoundaries documents `boundarySource`, `boundaryLicense`, `sourceDataUpdateDate`, `buildDate`, and `admUnitCount` as metadata fields, and describes ADM2 as the second subnational level ([API field definitions](https://www.geoboundaries.org/api.html)). The specific source agencies, vintage and license above come from the retained source metadata, not the current generic geoBoundaries license description. The pinned #443 source register records 525 features for the restored full object while its pinned metadata declares 526 ADM2 units; the mismatch remains unresolved. The corrected 214-subject extract cannot establish national completeness.

The neighboring Georef material is an official statistical normalization/comparison service. Datos Argentina describes its territorial datasets as compiled from IGN, BAHRA and INDEC publications and lists a CC BY 4.0 license ([official dataset record](https://datos.gob.ar/dataset/jgm-servicio-normalizacion-datos-geograficos)). The retained comparison snapshot has a later retrieval vintage and mixed `Departamento`, `Partido`, and `Comuna` granularity. It is not a legal-boundary adjudication or a ring-count source. A coordinate interior ring is only a structural observation in the retained source; its physical or legal meaning, current boundaries, and island identity are unresolved. This erratum does not change geography, approve the region, authorize import, or publish data.

## Handoff

This issue's bounded runtime-integrity acceptance is addressed by the guarded entry point and its new vintage. National source restoration and the source/legal/physical questions above remain with their existing evidence records; no geography correction or engineering integration is proposed by this packet.
