# WorldAtlas Data Strategy

This document describes the design for the full project. The [pipeline guide](../scripts/map-build/README.md) describes the current build.

## Contents

- [1. General](#1-general)
  - [Architecture and data lifecycle](#architecture-and-data-lifecycle)
- [2. Geography](#2-geography)
  - [Geographic framework and grid](#geographic-framework-and-grid)
    - [Map projection and dimensions](#map-projection-and-dimensions)
    - [Geographic hierarchy](#geographic-hierarchy)
    - [Classifying and assigning cells](#classifying-and-assigning-cells)
    - [Land rules](#land-rules)
    - [Water rules](#water-rules)
    - [Editable records and published grid](#editable-records-and-published-grid)
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
    - [Subordination relationship](#subordination-relationship)
    - [Primary government type](#primary-government-type)
  - [D. Trade relationships](#d-trade-relationships)
  - [E. App representation](#e-app-representation)

## 1. General

### Architecture and data lifecycle

Geography and historical attributes use three kinds of records.

1. **Evidence** retains original sources, conflicting claims, and their links to conclusions. Store original files of any size in R2. Neon records their references, dates, and checksums.
2. **Editable data** stores geometry, values, reasoning and provenance in Neon. Versioned construction records describe how to regenerate source-derived geography.
3. **Published releases** contain the reviewed map, viewer and metadata for an exact saved input selection.

Workers can edit separate areas in parallel. Those edits do not change the published website, which reads immutable release files from R2. Build a numbered candidate, review its exact files and inputs, then publish those same files. Approval belongs to the candidate; individual editable records do not need a separate draft/accepted workflow.

GitHub tracks code, schemas, documentation, and task issues. The user merges pull requests.

## 2. Geography

### Geographic framework and grid

#### Map projection and dimensions

Use a flat, 2D equirectangular (Plate Carrée) map with equal longitude and latitude steps of 0.00274658203125°. The full-world reference grid is 131,072 × 65,536. Keep the northern edge at 90°N and crop the map at about 60°S. Aligning the crop to a row edge gives a final grid of 131,072 × 54,614 cells (7,158,366,208), with a southern edge of 60.0018310546875°S.

#### Geographic hierarchy

Use the same geographic hierarchy throughout history. From smallest to largest, the levels are **location → province → area → region → subcontinent → continent**. Start with six land continents, excluding Antarctica, plus ocean groups. Give each unit one fixed display name based on the current reference.

#### Classifying and assigning cells

Use each cell’s center to determine whether it is land or water and which location it belongs to. If a cell’s center falls exactly on a boundary shared by two or more locations, assign it to the location with the lowest stable numeric ID. Every cell within the map’s coverage belongs to exactly one land or non-river-water location.

Investigate gaps and overlaps in source polygons before using them. Document any approximation and its consequences.

#### Land rules

Assign every land cell to an ordinary location. Use reasonably recent, reliable administrative boundaries, with older boundaries where necessary. Record each source date. Locations can use different reference dates with no common reference year. Keep the chosen boundaries fixed across history.

Research sparse areas in proportion to their significance. Locations have no imposed maximum size. Check lower-level administrative boundaries for compatibility before approving a higher-level division. User-approved subdivisions must cover every cell in their parent area without gaps, overlaps, or cells outside the parent.

We chose a grid resolution fine enough to give every important inhabited island and every island of historical or geographic significance at least one land cell.

#### Water rules

Non-river-water locations are named and selectable. Land-continent groups include nearby seas, island-region waters, and lakes. Ocean groups cover the remaining ocean waters. Broad waters may be grouped with relevant continents. Adjacent groups may share large seas. Some lakes may be too small to appear at this resolution.

**Bounded and shared seas.** Group these seas separately using documented geographic limits, including their bays, sounds, and passages. List the waters that belong to each sea group. A source dataset may draw the main sea, its bays, and its passages separately. Apply the chosen geographic boundary convention consistently when source conventions differ.

**Open coasts.** Use a uniform 12-nautical-mile (22.224-km) buffer. Measure the shortest distance along the WGS84 ellipsoid between the center of each water cell and the centers of coastal land cells on the grid. Where buffers overlap, use the nearer coast. Source islands absent from the land grid do not generate buffers. The buffer defines a geographic grouping for this map.

**Ocean assignments and connections.** Verify ocean labels and check which cells connect by shared edges, across all oceans and within each one. Include connections where the map’s left and right edges meet. Explain any expected separations.

**Enclosed water.** If a connected patch of water marked as ocean is surrounded by one continent, assign it to that continent. If the patch borders several continents and it is unclear which one it belongs to, review it before assigning it.

#### Editable records and published grid

Store editable geography records in Neon/PostGIS with stable numeric IDs, names, hierarchy levels and parents, and source polygons. Each location also records whether it is land or water. Code derives the approved hierarchy, app tables, river display and selection data, and the canonical cell grid. Neon holds the approved hierarchy and metadata. R2 holds the canonical cell-ID grid.

Store one canonical logical grid. Use a compact lossless encoding such as row runs so the builder can write the grid incrementally and the viewer can load it all up front. In the location grid, each unsigned 16-bit value stores a location ID. Reserve 0 during construction, leaving 65,535 usable values, and widen to 32 bits if needed. Every published cell has an assignment. Compression size depends on the final geography.

### Research, cell review, publication, and rivers

Generate candidate cell assignments from polygons and research inputs. For each proposal, record the geographic unit being divided, such as the province when proposing its locations. Store each proposal in Neon with its sources, reasoning, review status, and starting revision. Use the same approach at every level of the hierarchy. Keep incomplete or invalid drafts when they can be corrected. Check IDs, hierarchy, and whether the source geometry can be used. Each cell in the approved parent area must belong to exactly one child area, and every child cell must be inside the parent. Investigate source-polygon gaps and overlaps. Check conflicts against the affected records and relevant parent boundaries. Separate areas can proceed in parallel, and work can continue in one area while the same level is still being completed elsewhere.

Each geography-research scope has one accountable owner from research through validation and delivery; separate areas can proceed concurrently.

Rasterize each proposal to actual map cells at the chosen resolution, using IDs for that hierarchy level. The previews are temporary. The final location grid is canonical. At each level, the user approves the rendered cell map. Show the approved parent boundary and labeled, color-coded child cells. Let the user zoom, pan, and inspect sources and reasoning. Highlight issues and inhabited-island exceptions. Only valid, user-approved proposals feed the next level or publication. A change to an approved parent requires renewed cell-map approval.

Build one release candidate from the selected geography and viewer code. Review the rendered candidate and record approval for its exact files and inputs. Publish shared-grid updates one at a time. Verify the candidate files, record the release and its grid references in Neon, then switch the homepage to those same files. The working geography remains editable for future releases.

After all locations are finalized, complete a dedicated river-data and map-review pass before historical attribute research. Rivers are selectable line overlays with names and details, enough tolerance to select a river near its line, and minimum visible width. River overlays preserve underlying cell location IDs. Store river IDs, names, source lines, and geographic access links.

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

Each location attribute declares land, water, or both applicability. Time-dependent location attributes 1–15, including political control, port functions, and production, apply to land. Among time-agnostic attributes, Topography and Climate apply to land; Water type applies to water. The database rejects assignments that conflict with declared applicability. Water locations show Not applicable for land-only attributes. Attributes 3–6 and 8–10 are Not applicable when population is zero, as specified below. The app distinguishes Not applicable from Unknown. Each newly added attribute declares its applicability individually.

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

2. **Location rank:** Classify the whole location as Uninhabited, Rural, Town, City, or Unknown according to historical character. Uninhabited means population zero; use it only when supported by evidence or a justified estimate. Sparse records, lack of permanent settlement, and present-day population alone do not establish uninhabited status; consider historical and seasonal habitation. Rural covers inhabited non-urban locations, including nomadic populations. A Town or City may include suburban areas and countryside. For inhabited locations, population size alone does not determine rank.

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

Research both measures for the same location, year, and fixed boundary. Use the independently researched Population (#1). With compatible definitions and units and a known positive population, calculate Total GDP as GDP per person × Population, or GDP per person as Total GDP ÷ Population. If both measures are supported, use the one with stronger evidence as the basis for the calculation. If only one is supported, use it to calculate the other when possible. Mark a value Unknown when the evidence and calculation cannot establish it. At zero population, both are Not applicable. Retain all source evidence and the reason for the choice.

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

   See the [GloH2O Köppen–Geiger dataset](https://www.gloh2o.org/koppen/) and [Beck et al. (2023)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10593765/).

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

Notable production (#15) and trade reference the same product catalog by stable ID; it may expand as research identifies notable goods. Qualitative production and trade records are the foundation; add product quantities when supported. For each measured quantity, record the product, amount, unit, and year or period it covers. Distinguish annual output, individual shipments, and multi-year totals. Prefer product-specific units. When a conversion or estimate is justified, retain the original measurement and how the new value was calculated. Use Unknown when there is no defensible quantity. Use zero only when evidence or a justified estimate supports it.

Each trade quantity belongs to one year within the connection’s active period. Keep multi-year totals as source evidence. Record a figure for a particular year only when the evidence supports that year’s figure or a justified estimate.

Record significant directed connections between existing geographic units (location, province, area, region, subcontinent, or continent) or political entities. Endpoints may use different levels. Record from/to endpoints, active year or inclusive year span, one or more shared product IDs, transport by land, river, sea, or a known combination, and evidence or estimate basis. A location may trade goods it does not produce locally.

Keep each connection at the geographic level supported by its evidence. A regional record does not imply known flows for contained locations. Retain sources whose coverage does not sufficiently match an endpoint as evidence without assigning an exact endpoint quantity. Do not sum regional totals together with contained detailed flows.

### E. App representation

Map and detail views use the same accepted data for the selected year. Time-dependent values follow that year; time-agnostic attributes remain fixed. Present estimates much like evidence-backed values in the clean primary view; show provenance, estimate basis, and uncertainty in details on demand.

Detailed database schema, indexes, and mode-specific UI behavior remain for later design.
