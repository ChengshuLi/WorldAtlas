# Stable categorical presentation

The political map and its legend use the same display key: the retained source
category ID plus its source-supplied displayed name. The name matters because
some upstream records use one entity ID for concurrently displayed political
names. This key is presentation only: it neither splits source entities nor
changes ownership, provenance, geometry, dates or historical records. Explicit
unknowns retain `#53615c`. Culture and religion use the same display distinction;
fixed environmental classifications and geographic hierarchy retain their IDs.
Population retains its numeric logarithmic gradient.

Political colors are prepared offline from a fixed graph, not recolored for each
year or viewport. The pinned canonical raster supplies shared horizontal and
vertical cell edges, including horizontal date-line wrap. A separate nearby
constraint includes horizontal water gaps up to eight pixels on a 1024-pixel
world map. This is screen proximity, not a geographic-distance assertion. Exact
half-open source interval intersections supply historical category pairs; actual
concurrent names sharing a source ID are also constrained. The modern 2026
reference uses the application's normal resolver. No source interval envelope is
used as evidence of overlap.

The deterministic assignment orders graph nodes by degree and ID, uses an
ID-seeded candidate order and four bounded improvement passes. Unconstrained
names of the same original ID prefer the same color. The generated registry is
fixed across years and reloads. Its candidates avoid neutral/dark fills and favor
contrast against the unknown fill. GPU and Canvas receive the same RGB hex fills;
legend swatches use those values. Selected borders remain separate from fills.

## Criterion and limits

The engineering criterion is Euclidean OKLab distance multiplied by 100: at
least 8 under normal vision and 4 under each full-severity Machado 2009
protanopia, deuteranopia and tritanopia linear-sRGB model. These are engineering
thresholds and modeled comparisons, not a physical accessibility certificate or
WCAG text contrast claim. The retained report includes all failing baseline
pairs; passing colors are measured after quantizing to their actual RGB bytes.
Small territories, borders, zoom, displays and individual vision still affect
readability, so browser evidence complements these measurements.

Pinned political coverage includes all prepared source ownership intervals and
the modern geographic reference. Future/hosted-only categories are outside those
pins: they fall back to the original deterministic identity color until the audit
is refreshed. Vertical water-gap proximity is not included. Geography, culture,
religion, rank and environmental modes preserve their existing classifications;
the fixed political graph does not establish a contrast guarantee for their
unreviewed or different category graphs. Shared named modes receive the general
identity/name distinction, but their unseen adjacency requires separate pinned
inputs rather than invented evidence. Geographic location mode has tens of
thousands of units, so global uniqueness is neither practical nor a readability
certificate. Borders, selection, names and inspection remain necessary.

## Reproduction

Evidence for issue 23 lives in
`data/engineering/palette-contrast-20261003-7e91/`. The source interval and raster
manifests/hashes are pinned in the reports. The source audit reads original
records without altering them. On a fresh owned evidence directory, prepare the
raster-neighbor receipt, then run:

```sh
node scripts/audit-palette-raster.mjs data/engineering/JOB
python scripts/audit-palette-inputs.py --outdir data/engineering/JOB
python scripts/audit-palette-all-times.py --directory data/engineering/JOB
node scripts/audit-category-palette.mjs data/engineering/JOB all-times-modern
node scripts/install-category-palette.mjs data/engineering/JOB
node scripts/install-category-palette.mjs data/engineering/JOB --check
```

`scripts/audit-shared-category-modes.mjs` assesses the unchanged nonpolitical
graphs against a matching static build, pinned reference records and prepared
evidence. The retained three-date assessment found below-budget pairs in
environmental and several hierarchy modes; these counts are limitations, not
passing contrast claims. At the sampled years culture, religion and settlement
rank had no supported categories in these inputs; that absence does not certify
their contrast or historical coverage. These modes require bounded follow-up
graphs rather than borrowing the political graph's passing result.

Audit outputs refuse to overwrite earlier evidence. The installer rejects stale
source/grid pins and below-budget results. The generated palette is reviewed as
presentation data separately from executable source changes. Publication still
requires the normal claim, merge, package and sole-publisher protocols.
