# Smithsonian Benin object and image-rights evaluation

Issue: [#69](https://github.com/ChengshuLi/WorldAtlas/issues/69)

Campaign: `smithsonian-benin-media-20261003-1e2b2c5a1345`

Evaluation date: 2026-10-03 (America/Los_Angeles); source pages retrieved 2026-10-03 UTC.

Collection unit: Smithsonian National Museum of African Art (NMAfA).
Source collection: NMAfA object catalog, discovered through Smithsonian collection-image search and checked against each individual object page.

## Result

The five selected NMAfA catalog records describe objects associated by the museum with the historical Kingdom of Benin. The records provide coarse object-date strings, maker/style or court associations, and item-specific image restrictions. All five individual pages say **“Usage conditions apply”** under “Restrictions & Rights.” None is marked CC0 on its object page, so none is cleared for reuse as open-access media by this evaluation. Do not download, upload, or redistribute their images without separate permission. The Smithsonian's general Open Access program and site-wide terms do not override these item-level restrictions.

Catalog `Date` is reported as written, without turning centuries or ranges into exact year intervals. These dates describe the catalogued object, not its acquisition, photography, publication, or collection history. The selected pages do not give a dated chain of custody for any of the five. Donor/credit-line text is not treated as a provenance date. “Benin kingdom court style” and ceremonial/iconographic descriptions are source attributions, not proof that an item came from a particular excavated place. One object has a broader-than-search-window date that crosses 1897; it is not clipped to 1897.

## Selected records

| Smithsonian accession | Catalog title | Catalog date, verbatim | Cataloged Benin relationship and territorial wording | Image rights / decision |
| --- | --- | --- | --- | --- |
| `nmafa_2005-6-2` | Crest mask | `18th century` | Maker: “Benin kingdom court style.” Label text says the mask is worn in the Ododua ceremony and commemorates the founding of the Benin kingdom. Geography: `Nigeria`. No specific findspot or custody chain is supplied. | “Usage conditions apply”; not verified CC0; do not reuse image. |
| `nmafa_2002-19-3` | Ceremonial sword | `Late 19th century` | Maker: “Benin kingdom court style.” Label identifies the eben as associated with the oba's Benin Kingdom court. Geography: `Benin kingdom, Nigeria`. | “Usage conditions apply”; not verified CC0; do not reuse image. |
| `nmafa_2002-19-2` | Ceremonial sword | `Late 19th-early 20th century` | Same cataloged eben/court context as `nmafa_2002-19-3`; separate accession record and image. Geography: `Benin kingdom, Nigeria`. | “Usage conditions apply”; not verified CC0; do not reuse image. Catalog date spans across 1897 and is retained verbatim. |
| `nmafa_85-19-5` | Pendant | `Late 18th to mid-19th century` | Maker: “Benin kingdom court style.” Label describes court regalia and imagery on palace plaques. Geography: `Nigeria`; the record does not give a more precise provenance. | “Usage conditions apply”; not verified CC0; do not reuse image. |
| `nmafa_2005-6-36` | Salt cellar | `16th century` | Maker: “Benin kingdom, Bini-Portuguese style.” Label says it was carved for export to Europe. Geography: `Nigeria`; no dated custody chain is supplied. | “Usage conditions apply”; not verified CC0; do not reuse image. |

The two ceremonial swords are separate Smithsonian catalog records, but their parallel description, date wording and shared donor should be considered if a later campaign proposes separate historical entities. This evaluation does not infer a relationship between them.

## Source, access and rights

- NMAfA object records: direct, public Smithsonian pages linked below; access was available without authentication on the retrieval date. The metadata is restorable from those canonical URLs. No object image bytes were retained because each chosen item page applies usage conditions.
- Smithsonian Open Access program: <https://www.si.edu/openaccess>. Its public Open Access materials identify CC0-designated content as the reusable subset; a general institutional statement is not an image-specific license.
- Open Access FAQ: <https://www.si.edu/openaccess/faq/>; API documentation: <https://edan.si.edu/openaccess/apidocs/>; general site terms: <https://www.si.edu/termsofuse>. The per-record “Restrictions & Rights” field is controlling for this evaluation.
- A search filtered to the “National Museum of African Art” data source and `media_usage:CC0` did not surface these five records; their direct records independently state “Usage conditions apply.” Search filters are discovery aids, not substitutes for checking each record.
- No API key, login token, or private access was used or recorded.

## Scope and uncertainty

This is an evaluation of five source records only. It does not establish atlas subject IDs, a location-wide attribute, a final historic territory assignment, or the truth of a catalog date. Geography values such as `Nigeria` and `Benin kingdom, Nigeria` remain Smithsonian wording and are not interpreted as modern atlas footprints. No settlement totals, source population denominators, or intervals are involved. The object-date strings have century-level or range precision; no exact year, use period, manufacture span, or end date is inferred beyond those words. No current or post-1897 date is carried backward. The sources do not document the specific territorial limits of the Kingdom of Benin or permit the precise provenance of every object to be reconstructed.

No images or factual claims are prepared for import. The regional approval gate is still closed for new location-attribute imports, and these artifact/media records are outside this campaign's source-only stage in any event. A future media task would first need permitted rights for each chosen image, source-specific attribution, a supported existing entity/relationship contract, and any required reviewed subject/location scope.

## Restoration and hashes

The object pages and official policy pages below were fetched over HTTPS on 2026-10-03 UTC. Their complete response bytes were hashed for integrity but are not included in this campaign; fetch the linked public pages again to restore them. The page content can change, so compare a new digest rather than expecting a future retrieval to match. Hashes cover the fetched HTML response bytes, not image files.

See [`restoration-manifest.json`](restoration-manifest.json) for exact URLs, access status, digest algorithm, response lengths, and the separate image identifiers displayed by the catalog. No image bytes were downloaded.

## Reproducible method

1. Search Smithsonian collection images for `Benin court`, `Benin plaque`, and `Benin bronze`.
2. Restrict candidate records to the NMAfA data source. Do not select records merely because the word *Benin* occurs in an unrelated description or means the modern Republic of Benin/Dahomey.
3. Open each candidate's canonical object page. Record its displayed title, accession, maker, date, geography, relevant catalog language, image identifier(s), and “Restrictions & Rights” value.
4. Compare item-level rights with the Smithsonian Open Access/CC0 designation. Exclude restricted images from reuse even when related items or the institution's general program offer CC0 assets.
5. Preserve coarse dates and uncertain catalog attributions verbatim. Do not infer exact dates, specific acquisition events, archaeological context, relationships, or atlas locations.
