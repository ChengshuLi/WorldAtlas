# Namibia–Angola treaty-page erratum

This additive packet corrects the source locators in the immutable PR #1346 Kakeri assessment. It does not replace, regenerate, or modify any file under `research/geography/gap-source-namibia-angola-20261006/`.

## Source and scope

The cited work is League of Nations Treaty Series No. 2960, volume 129 (1932), containing the 1928 Kakeri Final Act and the 1931 exchange of notes. The exact retained volume is 7,801,132 bytes, SHA-256 `a8790efad550c33786a75e26466a241a1858fac902678d8d2a7c2ffb02b0903f`, and has 478 PDF pages. Its official host is the [United Nations Treaty Collection](https://treaties.un.org/doc/Publication/UNTS/LON/Volume%20129/v129.pdf). The volume is an official historical publication; no separate reuse license was found. The bytes remain at their original path, with restoration instructions and hash in the evidence manifest. This is source research and attribution, not a legal reuse determination.

One-based PDF pages and running printed page numbers agree from pages 158 through 176. The No. 2960 title page is PDF page 157 and has no running printed page number. The page map separates the exchange, Final Act, and language-specific schedules. In particular, beacon 47 is on English schedule PDF/printed page 166. PDF/printed page 165 is the Portuguese schedule's first page (beacons 1–35), not the English page with beacon 47.

The correction preserves the original coordinate (17°23′23.7″ S, 18°25′06.2″ E), described by the source as a limestone ridge 240 m west of the Okavango's west bank. The source says latitude was not astronomically observed for beacon 47 and its longitude method varies by beacon. This historical locator does not establish a present river bank, thalweg, datum transformation, state practice, or modern territorial boundary.

## Historical-to-corrected references

See `historical-to-corrected-locators.json` for each source claim, the erroneous historical locator, the corrected physical PDF and printed pages, and the observed content used to distinguish the pages. The four historical records are bound by exact hashes in `evidence-quality.json`: the producer, root assessment, both vintage assessments, and source-access receipt. Their previous reports, runs, controls, and publication receipts are also pinned. The erratum leaves every historical byte intact.

The context IDs in the issue are 10 retained ADM2 features: three Angola municipality records from source vintage 2018 and seven Namibia local-constituency records from vintage 2007. Their direct retained-reference parents (“Cuando Cubango” and “Kavango”) are explicitly open semantic-review geographic groupings, not verified current administrative containment. This citation-only packet makes no boundary or parent-child correction. Those semantics, source vintage, completeness, and neighboring granularity remain for their existing source/hierarchy review; no territory has been certified by these page findings.

## Reproduction

From the repository root, run the additive validator twice with two unused run names, for example:

```sh
python3 research/geography/namibia-angola-treaty-pages-1346-20261008/validate_treaty_pages.py --run-id treaty-page-audit-5
python3 research/geography/namibia-angola-treaty-pages-1346-20261008/validate_treaty_pages.py --run-id treaty-page-audit-6
python3 research/geography/namibia-angola-treaty-pages-1346-20261008/validate_treaty_pages.py --compare-runs treaty-page-audit-5 treaty-page-audit-6
node scripts/evidence-quality.mjs research/geography/namibia-angola-treaty-pages-1346-20261008/evidence-quality.json
```

Each execution reads authenticated immutable baseline bytes, scans the complete pinned world-index part inventory for all 10 declared context IDs, authenticates the complete treaty volume, extracts and checks the mapped pages, and checks all three false historical locator records plus the incomplete claim range. The exact production admission function is also exercised with altered, missing, and truncated source bytes. Each run writes a fresh exclusive vintage through `NewVintage`; controls also validate a correct in-memory fixture and preserve an occupied destination sentinel. `--compare-runs` first authenticates both complete publication receipts and their controls, then chooses a fresh comparison vintage derived from the run pair. It emits the reproducibility record only when both distinct runs used this exact validator source and their semantic output hashes match. These are bounded reporting/citation checks; neither reruns nor validates the prior 21-candidate raster analysis.

The earlier `treaty-page-audit-3`, `treaty-page-audit-4`, and `treaty-page-audit-repro-1` publications are retained as superseded preliminary work. Independent review found their byte-drift fixtures duplicated the hash predicate rather than exercising the shared production admission function, and their comparison output used a fixed vintage. The final acceptance executions are runs 5 and 6 with the later, reviewed method hash and fresh-pair comparison receipt.

## Findings kept unresolved

- The erroneous printed-page field occurs in beacon 47 in the root assessment and both published vintage assessments; the producer sets it to 165.
- The Final Act citation combines the acceptance exchange with the treaty text, omits PDF page 160 from its list, and stops the page list before the English beacon-47 schedule on page 166. The page map separates these claims.
- Historical coordinate methods vary; no modern datum or current bank geometry is supplied. The 21-candidate overlay, its 49 positive-area pairs among 210 comparisons, and non-additive water summaries remain historical outputs, not independently established geographic facts by this erratum.
- Neither source authenticity, citation correction, subject identity, structural checks, nor the older reproduction receipts establish present political status, legal interpretation, or geographic approval.
