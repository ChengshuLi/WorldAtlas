# GREG West African ethnic concepts and reuse review

Issue #63; source-only evaluation retrieved 2026-10-03 UTC. The packet preserves an at-most-25-polygon sample and evaluates the public GREG release, schema, source dates, rights evidence and limits. It does not assign an Atlas culture, define a boundary, create identities/categories, or import facts.

## Source and dates

ETH Zurich’s International Conflict Research GREG page describes “Geo-referencing of Ethnic Groups,” based on the *Atlas Narodov Mira* (ANM), and states a global total of 8,969 polygons in ESRI shapefile format. It links the public archive `GREG.zip`, group list and Weidmann, Rød and Cederman’s article/appendix. The requested citation is Weidmann et al. 2010, *Journal of Peace Research* 47(4):491–499, DOI [10.1177/0022343310368352](https://doi.org/10.1177/0022343310368352); Crossref dates online publication 2010-05-25 and print issue 2010-07-01.

The underlying atlas is the 1964 Bruk and Apenchenko edition. The article describes source maps as compiled in the early 1960s, but does not supply exact observation dates by group or polygon. Treat 1964 as the atlas publication date, not a universal dated observation. The downloaded shapefile’s DBF reports `DBF_DATE_LAST_UPDATE=2008-11-01` and its ZIP members carry 2008 timestamps; these are artifact metadata, not ethnic-settlement observation dates. The live website imprint says ©2023; that is neither a dataset edition date nor a rights grant. No annual or continuous interval is supported.

## Rights and access

The public GREG page and direct archive download were accessible without credentials. The page requests citation, but the page, ZIP sidecar metadata, appendix and paper disclosed no dataset-specific license or express permission to redistribute/adapt GREG. The ETH imprint’s copyright notice applies to the website; the article’s Crossref standard publication-reuse-rights metadata is about the article, not the data. Public download and citation instructions do not establish open-data rights. The upstream 1964 atlas is a separate work and no permission for reproducing it was found. Therefore reuse permission remains **unverified**: do not bundle GREG source files or geometry, and seek rights-holder clarification before redistribution, adaptation or import. Exact restoration URLs and hashes are in `source-manifest.json`; original bytes were kept outside the repository.

## Format, concepts and bounded examples

The actual archive contains a WGS84 polygon shapefile. GDAL confirms 8,969 polygon features. The appendix defines `FeatureID`, up to three group-ID fields (`G1ID`–`G3ID`, zero when not applicable), translated short/long labels, source polygon `AREA` in square metres calculated in Eckert VI equal-area projection, `COW` based on the 1989 international system, and two-character `FIPS_CNTRY`. There is no population count, denominator, share, or proportion field. The paper explains that source map territories can indicate up to three groups sharing an area. The identifiers’ G1/G2/G3 column order is not a population ranking; neither `AREA` nor label order supplies a primary group or primary culture. GREG’s “ethnic group” concept cannot be silently equated with the Atlas’s culture category.

For a small reproducible look, the manifest records the first 25 source-order features that intersect a rectangular query window from 5°W–5°E and 4–15°N. This envelope is only a broad Gulf of Guinea retrieval aid, not an Atlas region or territory boundary. The resulting examples include source FIPS/COW labels for the Ghana/Benin records; COW is expressly 1989 context. Repeated group IDs occur across multiple polygon features. Long/short labels and source areas are preserved as the publisher’s values. This is a purposive, non-random excerpt: no frequency, group prevalence, local majority, or territory assignment is inferred. Geometries are not retained.

The appendix says ANM maps ranged from 1:4,000,000 to 1:15,000,000. Authors georeferenced scans with distributed ground-control points (usually around 20/map), affine transformations and visual checks, then screen-digitized areas. It offers a roughly 0.5 mm map-position rule of thumb and approximately 10 km as a conservative general accuracy assessment at smaller map scales. This is not a polygon-specific error bound or statistical confidence interval. The article warns that the map was static, reflects early-1960s configurations, may be outdated after conflict/displacement, and has no time dimension.

## Suitability verdict

GREG is useful as a dated, source-linked representation of ethnic settlement geography and candidate concepts for further research. In this bounded West African sample, it does not support selecting a primary culture per polygon or Atlas location: multiple groups may share polygons, no group population proportions are encoded, and its boundaries are map-derived with kilometre-scale positional uncertainty. Country codes describe 1989 coding context, not territorial sovereignty at the ANM date. The exact dataset reuse license remains unresolved, so no data import or geometry redistribution is suitable from this evaluation. A later content project would need rights clarification, independently sourced dated population shares if a “primary” value is wanted, and the matching published regional certificate/exact approved subjects/release pins. The source-only finding closes only this bounded evaluation; it does not claim global ethnic/cultural coverage.

## Sources

Canonical source URLs, byte counts/hashes, archive metadata, methods and limits are recorded in `source-manifest.json`. No private credentials, full source dataset in Git, location assignments, boundaries, code/schema edits, or imports were used.
