# Romania #997 provenance and guarded reproduction

Research date: 2026-10-06. Scope is the 42 native location IDs in issue #1177, their 42 listed singleton framework parents, and seven neighboring administrative-source catalog rows. The issue's 27 whole-file input descriptors total 53,499,538 bytes. `input-manifest.json` preserves each commit/path, byte count and SHA-256. All 27 original files remain unchanged.

## Restoration provenance

The earlier follow-up's source-restoration note confused the upstream geoBoundaries commit with the WorldAtlas repository containing the retained source packet. GitHub API lookups establish that `9469f09592ced973a3448cf66b6100b741b64c0d` exists in `wmgeolab/geoBoundaries` and returns 422 in `ChengshuLi/WorldAtlas`; the original source files are retained in WorldAtlas commit `0de4b1f4183d6cf7c5fc6c78b6316f0f3a6b1e15`. The later crosswalk and its transcription/reproducer are retained in WorldAtlas merge `da9b0c46deb7b06027f2edd07016e0923cffde29`. See `SOURCE_RESTORATION.md` and `provenance-verification.json`. This corrects project restoration provenance while leaving upstream object-level lineage unresolved.

## Reproduction and scope

`reproduce_guarded.py` obtains each input directly from its declared immutable Git commit, checks whole-file lengths and SHA-256 digests, verifies the current issue 1177 snapshot against the captured contract digest and checks that its 27 pins and exact 42 IDs match. It byte-checks the original #997 contract, roster, neighbor transcription, generator, output, retained 2017 GeoJSON, source manifest, and all other declared inputs before compiling the pinned historical generator in memory. It also checks each of the seven neighbor rows against the pinned `data/administrative-sources.json` record (layer, label, count, vintage, source, license label and URL), then applies the prior generator's exact subject, source ID, name, and same-name singleton-parent checks. The seven copied metadata digest strings are not recomputed against separate upstream metadata objects; those objects are outside the retained input set.

Two separate commands wrote to fresh exclusive run directories. Each retains a deterministic gzip wrapper around the original 40,710-byte `source-crosswalk.json`; the decompressed bytes match the historical output exactly (SHA-256 `4272cd06a16f7c30e1128fae6d4bd2f41246f83997f565816190e78bf4cb563d`). The independent runs report 42 subjects, 42 distinct singleton parents, seven catalog rows, a 41+1 match to the retained roster transcription, 740,512 recursive source-coordinate positions, 8,119 Atlas positions, and zero exact geometry JSON matches. The last three values describe representation differences only; no polygon accuracy check or official vector comparison was performed.

Retained negative controls reject byte changes to the neighbor transcription, roster, #997 issue contract, original code, pinned hierarchy baseline, and source GeoJSON before generation. A specific Hungary ADM1 count change from 20 to 21 fails both the immutable whole-file guard and the parsed-context-to-catalog value comparison. The existing-output control preserves a sentinel and refuses to write into the occupied directory. Outputs are restricted to this issue-owned packet; the original source and report paths were not written.

## Geographic meaning, source and uncertainty

The checks confirm internal agreement among pinned repository data, the prior issue contract and the retained roster transcription. They are not an independent adjudication of administrative status. The 41-county/one-Bucharest distinction is reported as the prior packet's roster classification only; its law and statistical citations have not been newly authenticated in this erratum. The 42 `framework:province` parents remain internal same-name singleton wrappers, not evidence of a Romanian legal province tier.

The retained source metadata labels the layer 2017, 42 ADM1 features and CC BY 4.0. Its ArcGIS item ID differs from the World Bank catalog item ID; no object-level lineage or source-specific rights conclusion is made. The official 2024 ANCPI county archive was not obtained. The 0-of-42 exact geometry JSON matches compare a detailed source representation with simplified Atlas geometry; they do not establish boundary error, correctness, completeness or legal accuracy. Neighbor catalog labels, vintages and licenses are retained WorldAtlas catalog context, not authoritative legal equivalence.

## Engineering and research follow-ups

- Source maintainer: resolve the ArcGIS/World Bank item identity and rights lineage before any source repin.
- Geometry researcher: restore the listed 2024 ANCPI archive, retain archive/extracted hashes, license notice and CRS, then compare all 42 units individually against the 2017 source.
- Hierarchy owner: review the 42 singleton `province` wrappers and their consumers; preserve IDs unless a separately reviewed migration is approved.

This packet does not change source pins, IDs, geometry, hierarchy, releases or the earlier evidence. It does not certify the whole Romania region, approve geography, authorize imports or request publication.
