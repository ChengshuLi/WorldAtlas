Raised/recorded: 2026-10-02 (America/Los_Angeles).
Design finalized with the user: 2026-10-02 (America/Los_Angeles). Original draft date retained.

## Purpose and authorized scope

Add structural support for government, three economic metrics, primary spoken language, adult literacy, dated disease/outbreak impacts, major rivers/lakes, coastal contact, and ports. This is engineering: contracts, storage/migrations, registries, import validation, shared resolution, APIs/exports, UI and map modes. Filling actual historical facts is later history-research work; sourcing geographic water features is separate content/geography work. Do not attempt worldwide historical expansion or fabricate illustrative facts as real evidence.

This is an unclaimable engineering umbrella. Implementation uses the bounded children linked below, normally one PR and at most 1–3 PRs each. Read this ENTIRE specification plus the relevant child; no earlier chat is needed. Design is settled. Schema layout, exact codes, equivalence-scale choice and justified source-catalog inclusion criteria are documented implementation details, not permission to change the agreed semantics.

## Shared model, time, provenance and preservation

- Extend the existing model rather than create an unrelated database/UI. Use stable entity/category/metric/feature IDs; dated labels do not change identity.
- Government belongs to a political entity. Rivers, lakes, ports, diseases and outbreaks are linked entities/features/relationships. Locations remain territorial polygons with the existing complete single-parent geographic hierarchy.
- Use sparse supported half-open intervals, 3000 BC–2026 AD, no year zero. Never materialize one row per location per year or extend an observation merely to fill blank years.
- Every observation/relationship/derivation retains source IDs and original source bytes/hash references, supported interval/observation period, geographic scope/footprint or release pins, method, reference versus historical status, estimate status, uncertainty and source precision. Numeric measures retain their units and measurement definitions.
- Explicit unknown/unresolved is distinct from verified zero, false, no disease, no water contact or no active port. Missing imports, incomplete catalogs and failed reads do not establish absence.
- Deterministic shared resolution must agree across server, static/prepared exports, maps, legends, hover, selection and inspector. Preserve existing direct/derived/reference/example precedence and retirements. Modern reference observations must not silently become ancient facts. Reference feature geometry remains identified as reference when no dated evidence exists.
- Preserve all completed historical work, prior source bytes, stable IDs, imported claims, archived geography and immutable deployed migrations. Use forward migrations and backward-compatible contract/read paths.
- New facts can be imported later without editing application code or rebuilding location ownership geography. Feature-geometry revisions invalidate only relevant feature/contact assets unless location footprints actually change. Version reusable caches by applicable footprint/release, feature/source geometry and method.
- Keep current regional research gates. Structural support does not approve regional interiors or authorize factual imports into unapproved territories. Source-only staging and synthetic test fixtures may proceed under existing policies.

## 1. Government: one primary class per political entity/date

One resolved primary government class per political entity at the selected year, from a controlled, extensible registry with stable IDs and documented definitions. User examples: monarchy, republic, theocracy, steppe horde, tribal polity; allow other reviewed classes. Vocabulary entries are not assignments of actual governments to countries.

Real institutions may overlap conceptually, but the ATLAS PRIMARY CLASS is exclusive. Document classification rules for ambiguous cases; use explicit unresolved status where evidence cannot decide. Do not introduce multiple independent government traits, combination colors, or a mixed-government category for this feature.

All locations with the same resolved owner/year display that owner's same government class. Unknown owner/government yields unknown. Do not copy a polity's government into thousands of annual location records or infer it from religion, culture, present-day ownership or local administration.

Government map: all entities/locations classified as monarchy share its class color, all classified as steppe horde share another, etc. Category identity determines color, not individual country identity. Political mode still colors the owner and remains separate.

## 2. Economy: exactly three primary metrics

### A. GDP per person
Annual economic output per resident, the mean: total GDP divided by the supported resident population of the same territory/period. This is an output-based measure of prosperity, not the typical person's salary or spendable income.

### B. Total GDP
Canonical presentation: GDP per person × supported population. Preserve any directly reported total-GDP observations as source evidence and potential derivation inputs.

GDP per person = total GDP / population
Total GDP = GDP per person × population
Population = total GDP / GDP per person

Any two compatible quantities can infer the missing third, where mathematically defined. Compatibility requires the same actual territory/footprint, period, resident-population definition, measurement scope and economic price/unit basis. Avoid division by zero, circular derivations, extrapolation and combining independently incompatible source series. Inconsistent reported triples remain preserved and flagged for resolution; do not silently overwrite observed population or original GDP figures. Derived records retain input IDs, interval intersection, formula, units, estimate status and uncertainty. Rounded/modelled inputs do not justify exact output precision; inferred/rounded zero must not establish uninhabited land. Missing inputs produce unknown.

### C. Median purchasing power
Median household-size-adjusted disposable income, adjusted for the consumer prices people face; operational statistical definition: median equivalized real disposable household income.

Disposable income is after taxes and transfers. Equivalization accounts for household size/shared costs (two people do not require twice the housing expense). A typical implementation assigns each person their household's equivalized income and takes the person-weighted median, representing a single-person-household-equivalent living standard. Retain equivalence-scale/weighting definitions; do not label this as raw mean income per resident. Document cash/in-kind/subsistence coverage and valuation where the source supports it.

This is MEDIAN, not mean. Never derive a population median from mean income, GDP per person, a country's average, a single occupation's wage or an unsupported distribution assumption. A median multiplied by population is not aggregate income or GDP. Historical wages, consumption and basket-equivalent evidence may be retained as separately typed measures; they are not silent substitutes for this primary metric.

### Price comparability and maps
PPP handles price differences BETWEEN places; constant prices handle price changes OVER time, including inflation. GDP PPP covers the GDP expenditure mix (including investment/construction/government), while consumption PPP targets household goods/services. Do not automatically reuse a GDP PPP conversion for disposable purchasing power.

GDP fields use constant-price GDP-PPP units; median purchasing power uses constant-price consumption-PPP units. Record benchmark year (e.g. 2021 international dollars), PPP expenditure scope/series, original currency/unit, deflator/conversion methodology and supported comparability group. The example benchmark does not authorize undocumented conversion of other source series. Only compatible observations or supported conversions share a gradient/legend. Display metric, units and comparison basis clearly; detailed method stays in evidence.

An unchanged literal basket is not available/meaningful across all 5,000 years. Version basket definitions and preserve historical methods. No universal ancient exchange rate, arbitrary 0–100 development score, fabricated local allocation, interpolation or automatic country-average assignment is permitted. A defensible reconstruction/allocation can be imported as a labeled estimate with assumptions; absent such evidence remains unknown.

Provide three distinct economic map modes: GDP per person, Total GDP, Median purchasing power. Fills reflect one resolved value over the entire location.

## 3. Primary spoken language only

A controlled stable language ID describes the everyday/home spoken language used primarily by the largest share of residents where supported. Language is independent of culture; neither implies the other. Official language/writing system does not establish residents' spoken language. Ties/insufficient evidence remain unresolved.

No mandatory dialect or script/written-language field in this feature. Language-vs-dialect classification is not universally a strict hierarchy. Shared characters do not make Mandarin/Cantonese the same spoken language; source classifications must be documented. A source reporting only broad 'Chinese' is preserved as broad evidence, never silently refined into Mandarin/Cantonese. Historical language IDs/dated labels and reviewed broader classifications can be supported without inventing dialect detail.

Primary-language map colors whole locations by resolved spoken-language ID, independent of culture mode.

## 4. Adult literacy

Percentage of residents aged 15+ who can both read and write, with understanding, a short simple statement about everyday life (UNESCO/World Bank definition). Display 0–100%; define the storage unit explicitly so 0.8 and 80 cannot be confused.

Retain adult numerator/denominator or rate, cohort/age range, year, assessment method, source precision and uncertainty where provided. Total population is not the adult denominator. Different age cohorts and different literacy definitions do not silently share the canonical metric. Functional literacy, signatures and school attendance are separate/proxy evidence unless a documented supported method estimates canonical adult literacy. Zero is evidence, unknown is not zero; no adult denominator means no computable rate.

Add a location value and literacy gradient mode using the same resolved record.

## 5. Disease: concurrent outbreaks and selected-year mortality

Stable disease and outbreak identities, with dated links to affected locations. A location may have multiple concurrent diseases/outbreaks; this is not one disease dropdown or a unique disease owner. Inspector lists the documented diseases affecting it at the selected year, even if a mortality estimate is unavailable.

Normal disease timeline mode: estimated disease-attributed deaths DURING THE SELECTED YEAR as a percentage of a compatible supported location population denominator; higher percentage = darker whole-location fill. Retain estimated death counts, period, population basis and attribution method. Cases/prevalence and all-cause excess mortality are not automatically disease-attributed deaths.

Default combined mode represents the UNION of estimated distinct deaths across included outbreaks, not the sum of percentages. Deduplicate duplicate sources/descriptions of one outbreak and avoid counting one death multiple times under overlapping attributions. Add only compatible counts supported as disjoint, or use a supported combined estimate. Where overlap cannot be resolved, retain supported bounds or an unavailable aggregate; do not assume independence, invent a midpoint, or clamp to hide invalid aggregation. Subgroup-specific percentages with different denominators cannot be simply added.

A cumulative multi-year outbreak total is not an annual estimate and must not be repeated or spread uniformly across every year. Preserve cumulative evidence separately with its period; annual map remains unknown without supported annual allocation. Optional disease filtering can reuse the same contract, but all-outbreak annual aggregation is the normal mode. No mandatory arbitrary 'heavily impacted' thresholds.

## 6–8. THREE separate water/port map modes

The final design supersedes the earlier combined Coasts & seaports proposal. These are independent modes/values:

| Mode | Whole-location classification | Feature overlay |
| --- | --- | --- |
| Rivers & lakes | Binary contact/no contact with cataloged major rivers/lakes, plus explicit unknown | River lines, downstream arrows where known, lake areas, names and feature information |
| Coastal | Binary marine-shoreline contact/no contact, plus explicit unknown | Ocean/sea shoreline, names and information |
| Ports | Known non-port grey; maritime, river, lake and mixed types in distinct colors; explicit unknown distinct from none | Active port markers, names, functions/status and dated evidence |

### Rivers & lakes
Maintain a versioned, sourced major-river/lake catalog with documented inclusion rules and coverage. Do not attempt every stream. A location has contact if a cataloged major river CROSSES OR BORDERS its territory, or a cataloged lake shoreline lies within/borders it. Include interior lakes and border-running rivers, not just intersection with the location's exterior ring.

River/lake contact is not necessarily freshwater, drinking-water availability or usable transport: saline lakes and tidal/brackish rivers exist. Call the mode Rivers & lakes, not a promise of freshwater. Geometry/type, not the literal word 'sea' or salinity alone, distinguishes marine seas from inland lakes.

River entities/reaches retain geometry and downstream connections; show direction where supported, including unknown/bidirectional cases where appropriate. Major rivers can have waterfalls, rapids, seasonal shallows or dams, and different vessels have different requirements. Initial feature requires NO navigability survey or navigable-ocean-path computation. Contact only means contact with included features.

Precompute source-based location contacts and reusable overlays; document source precision/numerical tolerance and catalog completeness. No arbitrary proximity buffer/cell reassignment. Zoom/pan/resize and mode changes reuse assets; never rerasterize location ownership or repeat spatial intersection computations on navigation.

### Coastal
A location directly touches a marine ocean/sea shoreline. Inland lakes do not establish coastal contact. Marine shoreline contact does not establish a usable harbor, drinking water or a port. Keep true/false/unknown distinct; do not infer from location names, a centroid, nearby ocean pixels, port presence or political ownership.

Use applicable published location footprints and supported shoreline geometry. Preserve reference context and source dates; do not claim a modern coast was identical in every historical year. Shoreline changes need source-based revision/cache invalidation, not invented historical geometry.

### Ports
Port entities/facilities with stable IDs, dated operating status and dated location links. Coastal contact and port presence are INDEPENDENT. Maritime ports can be upriver (Hamburg connects to the North Sea via the Elbe); river/lake ports can be wholly inland, far from any coast, and without any navigable ocean connection. A river draining into the sea is not proof of a navigable maritime route. Ports do not require a town/city/metropolis rank and are not new geographical locations.

Classify functional service as maritime, inland river, inland lake; a facility or location may have multiple documented functions. Maritime capability is sourced functional evidence, not automatic inference from coast or river geometry. Navigability is not required for the initial river-contact feature.

Mixed applies only when at least two port-function types are explicitly documented among active ports in that location/year (including explicitly multi-function facilities). A seaport merely situated on a river is NOT automatically mixed. Preserve the full port list/functions in evidence; use ONE mixed fill instead of separate colors for every combination. Show mixed in the legend only when present in the selected-year data; actual prevalence is unknown until research fills records.

Known no active port = grey. No imported records/incomplete historical coverage = unknown, not non-port. Planned/closed ports do not count as operating; supported active intervals matter. Port-only content updates do not imply coastline changes, rebuild location footprints, or change ownership.

## UI, performance and verification

- Concise location fields/facts with readable units, selected-year values and port/outbreak lists. Preserve the existing historical title and always-present present-day reference. Keep source citations, methods, intervals, uncertainty, calculations and technical caveats in the collapsed Evidence & sources section rather than flooding the main panel.
- Whole-location fills in every mode, with the same values in inspector/hover/selection/legend. Rivers/lakes/port geometry is a feature overlay, not a second fractional political/attribute fill.
- Empty factual datasets are a valid initial state. Synthetic fixtures are explicitly test/example data and never silently enabled as real history. Demonstrate all new modes/import paths without filling the timeline.
- Meaningful tests: exclusive polity class/inheritance and dated changes; all valid GDP identities and zero/incompatible/circular cases; median-vs-mean and comparison-basis rejection; broad spoken-language evidence; adult literacy bounds/cohorts/proxies; annual vs cumulative mortality, duplicate/overlap handling and unknown vs zero; river-crossing/bordering/interior-lake contacts; saline lake vs marine coast; inland maritime/river/lake ports; documented mixed vs river-sited seaport; active/closed dates; incomplete coverage.
- Server/prepared/static/export/import parity, source/claim preservation and retirement behavior; geometry/source hash-based cache invalidation; representative browser/legend checks and zero ownership recompilations/uploads during navigation. Keep assets within current hosting budgets; unrelated storage/performance redesign is out of scope.
- Use fresh main, canonical per-issue claims, 1–3-PR bounded children, <1,000 non-test changed lines per PR, and serialized squash merge. Coordinate shared registrar/schema/API touch points; one designated publisher handles live rollout with rollback and unchanged audience. A normal merge must not automatically run provider-management migrations or deploy.
- Parent closes only when all engineering children, relevant parity/browser/publication checks, backward compatibility and research handover docs are complete. Actual worldwide factual research is NOT a closure requirement.

## Standards and project entry points

- https://www.worldbank.org/en/programs/icp/data
- https://data.worldbank.org/indicator/NY.GDP.PCAP.PP.KD
- https://data.worldbank.org/indicator/SE.ADT.LITR.ZS
- https://www.oecd.org/en/data/indicators/poverty-rate.html
- Read AGENTS.md, docs/THREE_THREAD_START.md, docs/WORKER_COORDINATION.md, docs/PARALLEL_WORK_PROTOCOL.md and existing storage/import/structural validation docs. Inspect current src/model.js, src/attributes.js, src/temporal.js, hosted/ snapshots/import/export contracts and deployed PostgreSQL/legacy schema before selecting a compatible extension. File hints are discovery entry points, not a mandate to rewrite them.

## Bounded engineering children

- [ ] #529 — Extend dated observation and feature contracts for the agreed atlas attributes (3-PR maximum; ready; closed items remain recorded)
- [ ] #530 — Add exclusive dated political-entity government classes and government map mode (2-PR maximum; depends on #529; closed items remain recorded)
- [ ] #532 — Implement GDP identity, median purchasing power and three economic map modes (3-PR maximum; depends on #529; closed items remain recorded)
- [ ] #531 — Add primary spoken language records, inspector field and language map mode (2-PR maximum; depends on #529; closed items remain recorded)
- [ ] #533 — Add adult literacy percentage with cohort validation and literacy map mode (2-PR maximum; depends on #529; closed items remain recorded)
- [ ] #535 — Model concurrent outbreaks and annual disease mortality with safe union aggregation (3-PR maximum; depends on #529; closed items remain recorded)
- [ ] #534 — Add major river/lake features, cached location contacts and Rivers & lakes mode (3-PR maximum; depends on #529; closed items remain recorded)
- [ ] #536 — Add independent marine-shoreline contact and binary Coastal map mode (2-PR maximum; depends on #529, #534; closed items remain recorded)
- [ ] #537 — Add dated maritime/river/lake ports and functional mixed-type Ports mode (3-PR maximum; depends on #529, #534; closed items remain recorded)

Only the contracts child is initially ready. Feature children can proceed in parallel after #529 closes; Coastal and Ports also depend on #534. Each worker claims only one ready child, preserving source history and coordinating shared integration points. No giant umbrella PR.

Decision history: the premature draft is superseded by this finalized specification. The former mean-income suggestion is replaced by median purchasing power; mandatory dialect/script detail is omitted; the earlier combined coastal/seaport coloring is replaced by three separate Rivers & lakes, Coastal and Ports modes. No feature implementation or factual import was performed by this issue-writing task.


Readiness coordination: dependency closure alone does not authorize a blocked worker to start. The issue-creation coordinator rechecks merged contracts, current scopes/dependencies and overlap, then explicitly marks each eligible child status:ready. Structural child completion never opens historical-content imports; regional certification gates remain separate.

