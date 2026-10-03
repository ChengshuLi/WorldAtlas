# New Zealand 1891 Wellington population and religion source evaluation

## Finding

The official Stats NZ historical publication contains religion tables at three explicit geographic levels: provincial districts, counties, and boroughs. For Wellington Provincial District, Part I Table VI (population) and Part III Table V (religion) agree exactly for the 1891 total and sex counts: 97,725 persons, 52,375 males, and 45,350 females. At the borough level, Wellington’s Table XVII population total and Table VII religion total also agree exactly: 31,021 persons, 15,189 males, and 15,832 females. The source headings name the same 1891 unit types in each paired table.

Both population and religion tables exclude Māori. The report says Māori counts are presented separately in Appendix C, for a separate February 1891 enumeration; those counts are not folded into the 5 April denominator. Table XVII explicitly labels its borough total as including Chinese and half-castes. Table VII is labelled “exclusive of Maoris” and its Wellington total matches Table XVII exactly. This is consistent with a shared non-Māori denominator that includes the separately identified Chinese and half-caste counts; the retained excerpt does not separate their religion responses.

The retained example is a purposive subset of 21 denomination/response-status rows plus the Wellington Borough total. Persons, males, and females are kept as published. The report’s categories “No religion,” “Unspecified,” and “Object to state” remain separate. No percentage, primary religion, self-identity or culture mapping is inferred. The category sample is not an exhaustive religious table.

## Source and dates

*Results of a Census of the Colony of New Zealand taken for the night of the 5th April, 1891*, submitted from the Registrar-General’s Office, Wellington, 5 December 1892; printed by authority by George Didsbury, Government Printer, Wellington, 1892. Source collection: [Stats NZ historic publications](https://www3.stats.govt.nz/historic_publications/1891-census/1891-results-census/). Exact HTML edition, source byte count, SHA-256, restoration URL, and directory date are in `source-manifest.json`.

The supported observation is one census night, 5 April 1891. The report’s submission/publication is in 1892. It provides source-era Provincial District and Borough totals; this packet treats each unit by its historical label and makes no modern geography equivalence or area calculation.

## Tables and interpretation

- Part I, Chapter 6, Table VI: provincial-district population excluding Māori, with counts across census periods. The Wellington 1891 values match Part III, Chapter 38, Table V, which reports religious denominations by provincial district and excludes Māori.
- Part I, Chapter 18, Table XVII: borough population excluding Māori, with totals explicitly including Chinese and half-castes and further breakdowns. Wellington Borough’s persons/males/females match Part III, Chapter 40, Table VII, “Religions of Persons, Males, and Females (exclusive of Maoris) in each Borough.”
- Table VII’s borough block containing Wellington is identified in the manifest by its header sequence. The sample keeps 21 selected rows from that block plus the table total. Other rows and denominations are not represented here and are not zero-valued by omission.

The religion table records the publication’s denomination headings and count values. No explanatory crosswalk to modern religious identities is asserted. The source does not quantify classification error, nonresponse error, or confidence intervals; this evaluation does not independently validate individual responses or territory footprints. It verifies table definitions and denominator consistency at two matching source-geography levels.

## License and attribution

Stats NZ’s copyright page states a CC BY 4.0 reuse license for its content unless otherwise noted and gives an attribution statement. No work-specific exception or separate license notice was visible on the historical report page. The selected old report is served in Stats NZ’s historic-publications collection. Retain the specified attribution when adapting the data; the exact wording and license-page hash are recorded in the manifest.

## Scope limits

This closes the source review for the Wellington Provincial District totals and an illustrative subset of Wellington Borough religion rows in this report. It does not transcribe all denominations, counties, other boroughs, or Māori religion, nor does it support any time interval beyond the 1891 census night. There is no approved regional certificate or matching permitted-subject/release pin for importing these data. No Atlas assignments, geography changes, or imports were attempted.
