# Madagascar source citation erratum for #1352 and #1368

This is a source-only correction to the retained Madagascar source handoff. It does not revise the original regional packet, its geometry, the 119 stable district IDs, the 22 parent groups, or any historical run. The earlier evidence remains an immutable record of what those runs asserted.

## Correct statutory citations

I restored the complete official PDFs from the Conseil National de Législation portal on 2026-10-08 and verified their full byte lengths and SHA-256 values against the records already retained in the source packet. I extracted the relevant pages with macOS PDFKit and visually inspected them. The PDFs are not copied into this directory because no explicit reuse license was found on the official copies. `source-corrections.json` records the canonical URLs, exact hashes and sizes, inspected pages, lawful restoration instructions, and the limits of this check.

| Instrument | Clause for conditional immediate effect | Journal publication clause | Promulgation shown in PDF |
| --- | --- | --- | --- |
| Law 2021-012 | Article 4, printed/PDF pages 2–3 | Article 5, printed/PDF page 3 | 2021-08-11 |
| Law 2023-012 | Article 5, printed/PDF page 3 | Article 6, printed/PDF page 3 | 2023-08-11 |

Neither document has an Article 7. The original source-restoration entry incorrectly attributes the conditional effect language to Article 7 for both laws. The exact radio, television, posting, and Journal Officiel publication dates were not established. Promulgation is not treated as proof that those separate publication events occurred on that date.

## Namorona transfer and boundary handoff

Law 2021-012's explanatory text on PDF page 1 expressly transfers Namorona commune from Mananjary district to Manakara district. The annex on PDF page 4 lists Namorona among Manakara's communes. The pinned 2018 COD-PS ADM3 file contains one `Namorona` record, commune `MG23209490`, under old district `Mananjary` (`MG23209`) and old region `Vatovavy Fitovinany` (`MG23`). This is the expected vintage difference, not evidence that the old row is wrong.

The retained COD-AB ADM2 comparison associates `Mananjary` (`MG26209`) with Atlas district ID `gb:MDG:ADM2:10022922B52512193010711`, and `Manakara` (`MG27210`) with `Manakara Atsimo`, Atlas district ID `gb:MDG:ADM2:10022922B29911348985828`. Both Atlas records currently share parent `framework:province:vatovavy-fitovinany:fd10ec52071e`. The prior comparison's symmetric-difference figures (0.741515803% for Mananjary and 1.049105499% for Manakara Atsimo) compare broad district polygons and do not locate Namorona or determine whether the district geometries include its transfer. The reproduction checks these exact archived values against the retained run-14 table and binds them to the original PR #1352 commit.

The engineering handoff must therefore examine the commune-level transfer as part of both district-source comparisons, while preserving both district IDs and the shared parent until a coordinated, sourced correction is separately accepted. The post-transfer commune code, exact commune territory continuity, and whether either retained polygon reflects the transfer remain unknown. No commune polygon was available in this source subset, and this erratum makes no boundary or parentage decision.

## Government portal reconciliation

The page captured from Torolalana on 2026-10-08 has a page description asserting 23 regions and 119 districts. Its server-rendered table contains 114 district rows, with identifiers 8–12 absent. The page shows Vatovavy and Fitovinany separately (including Mananjary under Vatovavy and Manakara under Fitovinany); it does not show the unsplit 2021 region. It still assigns Mananara-Nord and Maroantsetra to Analanjirofo and contains no Antanimora row. No visible page-update date was found.

This is contradictory, incomplete, undated service-directory evidence. It supports the limited fact of what the portal displayed at retrieval; it does not establish legal status, a complete district roster, boundaries, or effective dates. The full HTML response is not retained because the page has no explicit reuse license identified in this review. Its retrieval URL, date, byte length, SHA-256, exact relevant rows, and restoration procedure are in `source-corrections.json`.

## Inherited Antanimora evidence and remaining handoff

The later retained source ledger records Decree 2024-480 as scheduling Antanimora Sud under Ambovombe prefecture with eight named communes. Its recorded Article 3 makes effect contingent on radio/television publication; the exact broadcast date remains unknown. The same ledger records a 2026 INSTAT operational notice listing four communes (Ampamata, Imanombo, Jafaro and Andoharano). That notice serves an operational purpose and does not repeal or replace the decree's roster. The difference and any boundary implications remain unresolved.

The retained MapAction 2022 mapbook is only a secondary lead: its source note says it lists BNGRC, GADM and OSM inputs and depicts Antanimora Atsimo as commune `MG52516130` under Ambovombe-Androy. It does not establish legal continuity or polygon identity. The original BNGRC predecessor archive remains unrestored, and the former 2018 OCHA/HDX resource returned 404 in the prior investigation. `source-corrections.json` binds these inherited findings to the exact later source-restoration file and lists the remaining source, predecessor, legal-date and Namorona-boundary work with its existing owner. This erratum does not complete the broader #632 audit.

The reproducer uses the committed `issue-1509-api.json` as an immutable snapshot of the acceptance contract, subject IDs and source pins. Its recorded `state: open` is the API observation on 2026-10-08, not a live-state assertion; the snapshot is deliberately not refreshed when this issue closes. The reproducer therefore remains usable offline after merge.

## Reproduction and limitations

The one-command reproduction uses the issue-pinned Git baseline and the exact private source snapshots from the retrieval recorded in `source-corrections.json`. Restore the two laws and page to private files, check the byte lengths and hashes, then run:

```sh
python3 research/geography/madagascar-source-citation-1352-erratum-20261008/reproduce.py \
  --law-2021 /private/path/L2021-012-VF.pdf \
  --law-2023 /private/path/L2023-012_VF.pdf \
  --portal-html /private/path/regions-et-districts.html
```

The program reads only, emits a JSON report to standard output, and refuses changed source vintages. The source-backed validation run exercises the actual report entry point and pinned 2018 evidence. It checks wrong article references, removed portal rows, changed capture bytes, a missing Namorona record, a rebound old Namorona parent, and a rebound current affected-district parent. Re-run it with the same private source snapshots using `python3 research/geography/madagascar-source-citation-1352-erratum-20261008/test_reproduce.py` and the three source arguments above. The PDF text inspection was performed with PDFKit; independent substantive review should re-open the canonical pages.

This research does not establish legal effective dates, present-day commune geometry, source boundary accuracy, completeness of the nationwide administrative inventory, permission to redistribute source copies, or any approval for hierarchy edits, imports, or publication. The broader #632 geometry, predecessor, source-lineage, rights, and regional issues remain open under their existing owners.
