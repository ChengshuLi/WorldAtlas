# WorldAtlas Data Strategy

## Contents

- [1. General](#1-general)
  - [Architecture and data lifecycle](#architecture-and-data-lifecycle)
- [2. Geography](#2-geography)
  - [Geographic framework and grid](#geographic-framework-and-grid)
  - [Research, cell review, publication, and rivers](#research-cell-review-publication-and-rivers)
  - [Derived geographic relationships](#derived-geographic-relationships)
  - [Map rendering](#map-rendering)
- [3. History research](#3-history-research)
  - [A. General history research](#a-general-history-research)
    - [Shared data rules](#shared-data-rules)
    - [Research and review](#research-and-review)
    - [Catalogs](#catalogs)
  - [B. Location attributes](#b-location-attributes)
    - [Time-dependent location attributes](#time-dependent-location-attributes)
    - [Time-agnostic location attributes](#time-agnostic-location-attributes)
  - [C. Political entities](#c-political-entities)
  - [D. Trade relationships](#d-trade-relationships)
  - [E. App representation](#e-app-representation)

## 1. General

### Architecture and data lifecycle

Geography and historical attributes use three logical responsibilities:

1. **Evidence** retains original sources, conflicting claims, and their links to conclusions. Store original files of any size in R2; Neon tracks references, dates, and checksums without duplicating source files.
2. **Research** stores versioned geometry, values, reasoning, provenance, and review state.
3. **Published data** exposes only accepted records to the app.

These are logical roles, not a requirement for three separate databases or duplicate copies. Drafts stay out of the app. Keep the accepted revision visible until a replacement is validated, reviewed, and accepted; make acceptance and app visibility atomic.

GitHub tracks code, schemas, documentation, and task issues; the user merges pull requests.

## 2. Geography

### Geographic framework and grid

Use a flat, 2D equirectangular (Plate Carrée) map with equal longitude and latitude steps. The fixed, time-agnostic geographic hierarchy is **location → province → area → region → subcontinent → continent**. Use reasonably recent reliable administrative boundaries, older where necessary; record source dates and allow different reference dates by location, with no common reference year. Freeze chosen footprints across history. Use one fixed, current-reference display name for each unit.

Start with six land continents, excluding Antarctica, plus ocean groups. Every cell within the chosen map coverage belongs to exactly one land or non-river-water location. Land-continent groups include nearby seas, island-region waters, and lakes; ocean groups cover remaining ocean waters. Broad waters may be grouped with relevant continents, and large seas may be shared by adjacent groups. Non-river-water locations are named and selectable. Ordinary open coasts use a uniform 12-nautical-mile (22.224-km) buffer from represented land cells, measured on a sphere; nearer coasts resolve overlaps. Source islands absent from the land grid do not generate buffers. Bounded and shared seas are grouped separately by documented geographic limits, including their constituent bays, sounds, and passages. Maintain explicit sea-family coverage rather than treating a source’s label polygon as a complete basin. Check ocean-parent assignments and four-edge connectivity globally, both across all ocean cells and separately for each ocean label, with longitude wrapping. Document legitimate separated marginal basins; apply the chosen geographic boundary convention consistently when source conventions differ. An ocean-code component enclosed by a single continent inherits that continent; ambiguous multi-continent components require review. The distance is a geographic convention, not a representation of national territorial waters. Small lakes and islands may not resolve at this scale. Flag inhabited islands too small to resolve during the first continent review and assess whether a higher resolution is warranted.

Every land cell belongs to an ordinary location. Research sparse areas in proportion to their significance; locations have no imposed maximum size. User-approved subdivisions fully cover their parent cells without gaps, overlaps, or cells outside the parent. Check lower-level administrative boundaries for compatibility before approving a higher-level division. Investigate source-polygon gaps and overlaps, and document any approximation rule and its consequences.

Classify and assign each cell by its center point: use the land or water location containing that point. Stable numeric location IDs break exact shared-boundary ties. Investigate source gaps and overlaps rather than treating them as valid geography. Flag important inhabited islands that still have no land-cell centers for explicit review.

Use equal equirectangular steps of 0.0054931640625°. The full-world reference grid is 65,536 × 32,768; crop at nominal 60°S while retaining 90°N. Row alignment gives a final grid of 65,536 × 27,307 cells (1,789,591,552), with a southern edge of 60.0018310546875°S. Store one canonical, losslessly compressed logical grid using a compact lossless encoding, such as row runs, for bounded-memory generation and full up-front loading. Each unsigned 16-bit value is the numeric location ID itself; reserve 0 during construction, leaving 65,535 usable values, and widen to 32-bit if needed. Every published cell is assigned. Compression size depends on the final geography.

Editable geography records in Neon/PostGIS use stable numeric IDs, names, hierarchy levels and parents, and source polygons; locations also record land or water type. Code derives approved hierarchy, app tables, river display/selection data, and the canonical cell grid. Approved hierarchy and metadata are in Neon; the canonical cell-ID grid is in R2.

### Research, cell review, publication, and rivers

Generate candidate cell assignments from polygons and research inputs. Save parent-bounded proposal versions with sources, reasoning, review status, and a base revision; incomplete or invalid drafts may be retained for correction. Validate IDs, hierarchy, source-geometry usability, and the partition against approved parent cells: every parent cell is assigned once, with no gaps, overlaps, or cells outside the parent. Investigate source-polygon gaps and overlaps. Check conflicts only against affected records and relevant parent boundaries so separate areas can proceed concurrently; intermediate levels do not require worldwide completion.

Each geography-research scope has one accountable owner from research through validation and delivery; separate areas can proceed concurrently.

Rasterize each proposal to actual map cells at the chosen resolution, using IDs for that hierarchy level. These previews are transient; only the final location grid is canonical. At every level, the user reviews and approves the rendered cell map, not polygons or vertices: show the approved parent-cell boundary and labeled, color-coded child cells, with zoom/pan, selectable sources and rationale, and highlighted issues or inhabited-island exceptions. Only valid, user-approved proposals feed the next level or publication. A change to an approved parent requires renewed cell-map approval.

Serialize shared-grid publication: derive from approved geography, upload a versioned grid to R2, recheck relevant revisions, then transactionally commit matching Neon results and the grid reference. Failed publication leaves the previous revision active; the app reads matching revisions.

After all locations are finalized, complete a dedicated river-data and map-review pass before historical attribute research. Rivers are selectable line overlays with names and details, practical hit tolerance, and minimum visible width. River overlays preserve underlying cell location IDs. Store river IDs, names, source lines, and geographic access links.

### Derived geographic relationships

After geography is finalized, derive adjacency from map cells and recompute it when geography changes. Two locations are neighbors when their cells share an edge. Store neighboring location IDs for every land and water location.

For land locations, derive lake access from neighboring locations classified as Lake, and coastal access from neighboring marine-water locations; a derived Yes/No coastal flag may be useful. Keep lake and coastal access separate. Derive river access from finalized river paths intersecting or following location boundaries, linking river IDs to all nearby locations with geographic access. Rivers remain selectable overlays, not locations; location cell IDs remain intact beneath them. These links describe geographic access only.

### Map rendering

Present one continuous world map with horizontal longitude wrapping and vertically clamped panning. Load and verify the complete native-resolution cell data up front before enabling map interaction, retaining a compact lossless representation rather than expanding the whole world into a dense bitmap. Zooming, panning, and cell picking operate entirely on the loaded data, with viewer-device WebGL/GPU rendering; do not fetch new geographic detail or substitute a different-resolution overview as the user navigates. Show a loading state until the map is ready. Keep rivers, labels, highlights, and details as generic overlays loaded as needed. Use readable geographic names and familiar climate class names. Verify desktop and mobile responsiveness during implementation.

## 3. History research

### A. General history research

#### Shared data rules

Every attribute—location or political entity, time-dependent or time-agnostic—has a shared definition with a stable ID, display name, meaning, value type, applicability, and time behavior. Categorical values reference shared category IDs, names, and definitions. Numeric values include population and disease-death counts, rates, percentages, GDP, and other economic values. Each attribute specifies its own units, time basis, evidence or estimation rules, and any allowed derivations or conversions. Keep numeric zero, **None** (supported absence), **Unknown** (insufficient evidence), and **Not applicable** (the attribute does not apply) distinct.

Use whole years from 3000 BC through the current reference year, 2026. Display BC/AD dates with no year zero; interval start and end years are inclusive, so a period ending in 1600 is followed by one beginning in 1601. Represent approximate dates with a best-estimate year and preserve uncertainty in the evidence. Values may be intervals or point estimates; an annual record for every year is not required. For years between researched dates, use the best educated estimate with a method appropriate to the attribute.

Each location attribute declares land, water, or both applicability. Time-dependent location attributes 1–15, including political control, port functions, and production, apply to land. Among time-agnostic attributes, Topography and Climate apply to land; Water type applies to water. The database rejects assignments that conflict with declared applicability. Water locations show Not applicable for land-only attributes. Population-dependent attributes 8–10 are Not applicable when population is zero. The app distinguishes Not applicable from Unknown. Each newly added attribute declares its applicability individually.

Historical research and published values may share versioned tables. An accepted-record view or pointer selects published values from research history.

#### Research and review

Complete geography, including its river pass, before historical attribute research. Afterward, independent research scopes can proceed in parallel, with dependencies enforced only where relevant. Use multiple Luna-class research agents with an independent 6.1-Sol-level reviewer; scale the ratio to workload rather than fixing it. Scope batches by locations or entities, attributes, years, sources, values, and reasoning. Each batch has one accountable owner through validation and delivery.

Automatic checks cover IDs, applicability, units and value ranges, share constraints, conflicting intervals, and cross-attribute dependencies. The reviewer evaluates sources, estimates, and historical interpretation, then accepts a batch or requests corrections. Attribute work does not require routine user approval. Escalate uncertain judgments to the user with a concise issue, options, and recommendation; pause only dependent work while unrelated scopes continue.

Before accepting overlapping-year updates to the same subject and attribute, compare and reconcile them with the current accepted revision. Preserve version history, provenance, and original claims. Geography remains user-approved through its cell-map workflow.

#### Catalogs

Catalogs are shared lists of eligible discrete values; every entry has a stable ID, display name, and definition. Grow catalogs through research for cultures, religions (including Unaffiliated), spoken languages, infectious diseases, and products. Political entities also grow through research and follow the same stable-ID and review principles, while their richer time-bounded records are defined separately under C. Fixed option sets—including location rank, Topography, Water type, vegetation, port functions, and the 30 Climate classes—are defined by their attributes rather than expanded as research catalogs.

Researchers reuse IDs or propose additions as findings emerge. The independent reviewer checks duplicates, overlaps, subtypes, useful granularity, and consistent definitions across the affected catalog. Granularity is chosen for each catalog, not by one universal ranking. The reviewer owns editorial changes and their audit scope; uncertain cases are escalated to the user. A catalog entry may be reviewed with research that references it, reconciling concurrent duplicate proposals together.

Keep source detail in Evidence. Nonsemantic renames retain IDs. Duplicate merges reconcile references and conflicts; substantive merges, splits, or definition changes are reviewed with affected records and dependencies. Keep the accepted version until a coherent update is ready. A split does not require narrower values than the evidence supports; usually audit the affected scope, widening it when needed.

### B. Location attributes

All time-dependent location values retain their sources and estimate basis.

#### Time-dependent location attributes

1. **Population:** Total residents within the fixed location boundary at the selected time, including urban, suburban, and rural residents. Use supported counts or justified educated estimates, including zero, without double-counting residents. Population is researched independently and remains a fixed input to other calculations; it is not inferred from other attributes or adjusted to reconcile them. Use Unknown when no estimate is justified.

2. **Location rank:** Classify the whole location as Uninhabited, Rural, Town, City, or Unknown according to historical character. Uninhabited means population zero; use it only when supported by evidence or a justified estimate. Sparse records, lack of permanent settlement, and present-day population alone do not establish uninhabited status; consider historical and seasonal habitation. Rural covers inhabited non-urban locations, including nomadic populations. A Town or City may include suburban areas and countryside. Rank is independent of total population.

##### Shared rules for attributes 3–5

Record the resident category with the largest population share at the selected time; that share may be below half. Use evidence or a justified estimate. Use Unknown only when no primary category can be justified, and Not applicable when population is zero. Record sources and estimate basis.

Optional share breakdowns use one structure: **complete** accounts for the population, **partial** records some shares, and **unavailable** means no shares can be justified. A partial breakdown alone need not establish the largest category; a separately justified primary category may still be assigned, including from a defensible estimate when the breakdown is partial or unavailable. Retain supported or estimated shares with their basis.

3. **Primary culture:** The resident cultural group.

4. **Primary religion:** The resident religious affiliation; Unaffiliated is valid.

5. **Primary spoken language:** The residents’ main everyday or home language. For multilingual residents, assign each person to the language they use most in everyday/home life when estimating shares.

6. **Adult literacy rate:** Percentage of residents aged 15 or older who can read and write a simple everyday statement with understanding, in any language, at the selected time. Use supported figures or a justified educated estimate, with its basis; use Unknown when no estimate is justified and Not applicable for an uninhabited location.

7. **Political controller:** For each land location and time, record the effective controlling entity by ID. If control is divided, choose the entity controlling the greatest area within the fixed boundary. States and local communities, tribes, or councils may be entities. Use Unknown when no controller is supported by evidence or a justified estimate.

   For joint administration, use a documented administrative lead; otherwise, when comparable evidence supports it, use the entity with greater responsibility and resources. A stable entity ID breaks remaining ties. At population zero, record a controller, NoController, or Unknown. With positive population, record a supported controller or Unknown. NoController requires evidence or a justified estimate of no control; Unknown means evidence is insufficient.

##### Shared rules for attributes 8–9

Research both measures for the same location, year, and fixed boundary, using independently researched Population (#1). When definitions and units are compatible, derive Total GDP as GDP per person × Population or GDP per person as Total GDP ÷ Population. If both measures are supportable, use the higher-confidence value and derive the other; if one is supportable, derive its counterpart; if neither is supportable, mark both Unknown. Retain all source evidence and the selection rationale.

8. **GDP per person:** Annual economic output per resident for the fixed location and selected year, in constant 2021 international dollars using GDP purchasing-power parity (GDP-PPP). Record source and estimate basis; document a compatible conversion when using older source measures.

9. **Total GDP:** Annual total economic output for the fixed location and selected year, in constant 2021 international dollars using GDP-PPP.

10. **Median purchasing power:** Annual person-weighted median disposable household income after taxes and transfers, adjusted for household size and prices. This represents typical resident purchasing power. Express in constant 2021 international dollars using consumption PPP; record evidence and estimate basis. Use Unknown when no estimate is justified.

11. **Infectious diseases and outbreaks:** Record significant infectious diseases and outbreaks affecting a location and period; several may occur concurrently. Use shared disease and outbreak identities. A disease may be endemic and also have an outbreak. Record presence or absence from evidence or a justified estimate; mortality is researched separately and may be Unknown even when presence is known. Use Unknown when research cannot justify a value.

12. **Annual infectious-disease deaths:** For each location and year, record resident deaths from the diseases and outbreaks listed for that location and period in #11, using the same identities. Each disease count may be Unknown. Also record the combined count of unique people who died from those listed diseases, counting each person once after resolving duplicate reports within and across diseases. Use a supported count or justified estimate; if the combined count is Unknown, retain individual estimates. Record sources, coverage, and overlap reasoning. Calculate percentages using Population (#1). Scope is infectious-disease deaths.

13. **Vegetation:** One primary category for the whole land location at the selected time: **Forest** (dense tree cover, including jungle); **Woodland** (open tree cover with grass or shrubs between trees); **Shrubland** (bushes and shrubs dominate); **Grassland** (grasses dominate, including pasture); **Farmland** (cultivated crops, orchards, and plantations); **Sparse vegetation** (scattered plants with mostly exposed ground); **No vegetation** (essentially bare rock, sand, or permanent ice); or **Unknown**.

14. **Port functions:** For each land location and selected time, record the set of active functions: Maritime, River, and Lake; multiple may apply. None means evidence or a justified estimate supports no active port function; Unknown means no defensible conclusion. Base functions on actual operation at that time. A maritime port may lie upriver. Record functions for the whole location.

15. **Notable production:** List locally significant goods actually produced within the location at the selected time, including raw materials, processed goods, and manufactured goods, using the shared product catalog. Multiple goods may apply; examples include wheat, iron ore, livestock, fish, timber, textiles, porcelain, and steel. Production may use imported inputs; trade alone does not establish local production. Record sources and estimate basis. None means evidence or a justified estimate supports no notable production; Unknown means available research cannot establish it.

#### Time-agnostic location attributes

1. **Topography:** One primary category for the whole land location: Flatland, Hills, Mountains, Plateau, or Unknown.

2. **Water type:** One primary type per water location, based on local setting: Open ocean, Coastal waters, Inland sea, Narrows, Lake, or Unknown. Inland sea is an enclosed or semi-enclosed marine basin. Narrows includes straits, narrow channels, and constrained archipelago waters. High-elevation lakes are Lake.

3. **Climate:** A fixed present-day reference layer across the historical timeline. Use the published GloH2O Köppen–Geiger V3 historical raster for 1991–2020 as the working baseline; record version and reference period. After geography is finalized, overlay the raster and assign each land location its largest-area class, checking coverage and coasts. Keep all 30 classes and quantitative definitions; display familiar names and retain codes. Five broad climate families may be derived for display. Unknown is separate.

   - **Tropical:** Af — Tropical rainforest; Am — Tropical monsoon; Aw — Tropical savanna.
   - **Dry:** BWh — Hot desert; BWk — Cold desert; BSh — Hot semi-arid; BSk — Cold semi-arid.
   - **Temperate, Mediterranean:** Csa — Hot-summer Mediterranean; Csb — Warm-summer Mediterranean; Csc — Cool-summer Mediterranean.
   - **Temperate, dry winter:** Cwa — Humid subtropical, dry winter; Cwb — Subtropical highland, dry winter; Cwc — Cold subtropical highland, dry winter.
   - **Temperate, no dry season:** Cfa — Humid subtropical, no dry season; Cfb — Oceanic; Cfc — Subpolar oceanic.
   - **Continental, dry summer:** Dsa — Hot-summer continental, dry summer; Dsb — Warm-summer continental, dry summer; Dsc — Subarctic, dry summer; Dsd — Extremely cold subarctic, dry summer.
   - **Continental, dry winter:** Dwa — Hot-summer continental, dry winter; Dwb — Warm-summer continental, dry winter; Dwc — Subarctic, dry winter; Dwd — Extremely cold subarctic, dry winter.
   - **Continental, no dry season:** Dfa — Hot-summer humid continental; Dfb — Warm-summer humid continental; Dfc — Subarctic, no dry season; Dfd — Extremely cold subarctic, no dry season.
   - **Polar:** ET — Tundra; EF — Ice cap.

   Sources: [GloH2O Köppen–Geiger maps](https://www.gloh2o.org/koppen/) and [Beck et al. (2023)](https://www.nature.com/articles/s41597-023-02549-6).

### C. Political entities

Each political entity has a stable ID and one fixed familiar conventional name, including extinct entities; its name is time-agnostic. Record start and end year, leaving the end open for an entity that still exists. Controller references must fall within the entity’s lifetime. Identity follows political-state continuity: a change in ruler or government type alone leaves the entity’s ID and name in place. Distinct political states have distinct IDs even when they share a civilization or territory.

#### Subordination relationship

Record subordinate and overlord entity IDs, start and end year, and evidence or estimate basis when one entity holds superior political authority over another that retains its own government. An alliance or tribute alone does not establish subordination. An overlord relationship does not replace the local controller assigned to a location.

#### Primary government type

Store one primary type per political entity and time; locations receive it through their controller. Choose the best-fitting category for the governing arrangement, using Unknown when no classification is justified.

- **Monarchy:** government organized around a monarch.
- **Republic:** political authority exercised through civic institutions and public offices.
- **Theocracy:** religious authorities or institutions hold governing power.
- **Steppe horde:** a mobile steppe confederation organized around military and kinship leadership.
- **Tribal polity:** political authority organized through tribal communities and leadership.
- **Military government:** military authorities directly govern.
- **One-party state:** one ruling party monopolizes political power.
- **Personalist dictatorship:** governing power is centered on an individual leader.

When descriptions overlap, select the best-fitting type as primary.

### D. Trade relationships

Notable production (#15) and trade reference the same product catalog by stable ID; it may expand as research identifies notable goods. Qualitative production and trade records are the foundation; add product quantities when supported. Each quantity specifies product, amount, unit, and measurement year or period, distinguishing annual output from a shipment or multi-year total. Prefer product-specific units; convert only when justified, retaining the original measurement and conversion or estimate basis. Unknown means no defensible quantity, not zero. Trade quantities refer to a specified year within the connection’s active period.

Record significant directed connections between existing geographic units (location, province, area, region, subcontinent, or continent) or political entities. Endpoints may use different levels. Record from/to endpoints, active year or inclusive year span, one or more shared product IDs, transport by land, river, sea, or a known combination, and evidence or estimate basis. A location may trade goods it does not produce locally.

Keep each connection at the geographic level supported by its evidence. A regional record does not imply known flows for contained locations. Retain sources whose coverage does not sufficiently match an endpoint as evidence without assigning an exact endpoint quantity. Do not sum regional totals together with contained detailed flows.

### E. App representation

Map and detail views use the same accepted data for the selected year. Time-dependent values follow that year; time-agnostic attributes remain fixed. Present estimates much like evidence-backed values in the clean primary view; show provenance, estimate basis, and uncertainty in details on demand.

Detailed database schema, indexes, and mode-specific UI behavior remain for later design.
