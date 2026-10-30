# Attribute strategy

Location attributes may be time-dependent or time-agnostic. Political-entity government type is stored per entity and time; locations receive it through their controller.

## Data lifecycle

Geography and historical attributes use three logical layers: **Evidence** retains original sources and conflicting claims with links to conclusions; **Research** stores versioned values, reasoning, and review history; **Published data** exposes accepted records to the app. These are logical responsibilities, not a requirement for three separate databases or duplicate copies. Research and published data may share versioned tables, with an accepted-record view or pointer controlling app visibility.

Geographic polygons and research inputs generate candidate cell assignments. The user approves exact map cells at every hierarchy level, top-down; child levels partition approved parent cells. Corrections to approved assignments return for renewed cell review. Generate the matching location-ID grid and metadata and publish them as one accepted revision.

Drafts stay out of the app. Keep the current accepted revision visible until its replacement is validated, reviewed, and accepted; make acceptance and app visibility atomic.

## Names and identity

Names are time-agnostic. Each unit in the six-level geographic hierarchy has one fixed display name based on a current reference name set during geography research. Each political entity has one familiar conventional name, including extinct entities. A change in government type leaves the entity’s fixed name and stable ID in place.

## Shared attribute definitions

Every location and political-entity attribute, whether time-dependent or time-agnostic, uses a shared definition with a stable attribute ID, display name, meaning, value type, applicability, and time behavior. Categorical values reference shared category IDs, names, and definitions. Numeric values specify units and value rules.

Keep numeric zero, None (supported absence), Unknown (insufficient evidence), and Not applicable (the attribute does not apply) distinct.

## Shared time handling

Use whole years from 3000 BC through the current reference year, 2026. Display BC/AD dates with no year zero; interval start and end years are inclusive, so a period ending in 1600 is followed by one beginning in 1601. Represent approximate dates with a best-estimate year and preserve uncertainty in the evidence. Values may be intervals or point estimates; an annual record for every year is not required. For years between researched dates, use the best educated estimate with a method appropriate to the attribute.

## Shared location-attribute applicability

Each location attribute declares whether it applies to land, water, or both. Time-dependent location attributes 1–15, including political controller, port functions, and production, apply to land. Among time-agnostic attributes, Topography and Climate apply to land, while Water type applies to water. Water locations show Not applicable for land-only attributes; attributes 8–10 also show Not applicable when population is zero. The database rejects incompatible assignments, and the UI distinguishes Not applicable from Unknown (insufficient evidence). Later attributes declare applicability individually.

## Research and review

Complete the geographic hierarchy and final river review before historical attribute research. Afterward, independent research scopes can proceed in parallel, with dependencies enforced only where relevant. Use multiple Luna-class research agents with an independent 6.1-Sol-level reviewer; scale the ratio to workload rather than fixing it. Scope batches by locations or entities, attributes, years, sources, values, and reasoning.

Automatic checks cover IDs, applicability, units and value ranges, share constraints, conflicting intervals, and cross-attribute dependencies. The reviewer evaluates evidence, estimates, and historical interpretation, then accepts a batch or requests corrections. Attribute work does not require routine user approval; send uncertain judgments to the user with a concise issue, options, and recommendation. Pause only dependent work while unrelated scopes continue.

Before accepting updates for overlapping years of the same subject and attribute, compare and reconcile them with the current accepted revision. Preserve version history, provenance, and original claims. Geography remains user-approved under its existing cell-map workflow.

## Catalogs and quantities

Catalogs grow alongside research. Researchers reuse stable IDs or propose additions as findings emerge. The independent reviewer checks duplicates, overlaps, subtypes, useful granularity, and consistent definitions across the affected catalog. The reviewer owns editorial changes and determines their audit scope. Product granularity is curated editorially and may expand as notable goods are found; the reviewer handles routine changes and escalates uncertain cases. A catalog entry may be reviewed with the research that references it, reconciling concurrent duplicate proposals together.

Keep source detail in Evidence. Nonsemantic renames retain IDs. Duplicate merges reconcile references and conflicts; substantive merges, splits, or definition changes are reviewed with affected records and dependencies. Keep the accepted version until a coherent update is ready. A split does not force narrower values than the evidence supports; usually audit the affected scope, widening it when needed.

Production and trade use one product catalog with stable IDs, display names, and definitions. Qualitative records are the foundation; add quantities when supported. Each quantity specifies product, amount, unit, and measurement year or period, distinguishing annual output from a shipment or multi-year total. Prefer product-specific units; convert only when justified, retaining the original measurement and conversion or estimate basis. Unknown means no defensible quantity, not zero. Trade quantities refer to a specified year within the connection’s period.

## Time-dependent location attributes

For each time-dependent location value, record its sources and estimate basis.

### 1. Population

Total residents within the location’s fixed boundary at the selected time, including all urban, suburban, and rural residents. Use supported counts or justified educated estimates, including zero; record the basis. Use Unknown only when no estimate is justified. Research population independently and treat it as a fixed input when deriving or reconciling other values.

### 2. Location rank

Classify the whole location at the selected time as Uninhabited, Rural, Town, City, or Unknown, based on its historical character. Uninhabited means population zero; Rural covers inhabited non-urban locations, including nomadic populations. A location ranked Town or City may contain suburban areas or countryside within its boundary. Assign rank independently from population when historical character supports it; use Unknown rank when no classification can be justified.

### Shared rules for attributes 3–5

For each attribute, record the resident category with the largest population share at the selected time, including when that share is below half. Use evidence or a justified educated estimate. Use Unknown only when no primary category can be justified, and Not applicable when population is zero. Record sources and estimate basis.

Optional share breakdowns use the same structure for all three: **complete** accounts for the population, **partial** records some shares, and **unavailable** means no shares can be justified. A defensible estimate may establish a primary category even when the share breakdown is partial or unavailable. Retain supported or estimated shares with their basis.

### 3. Primary culture

The category is the resident cultural group.

### 4. Primary religion

The category is the resident religious affiliation; Unaffiliated is valid.

### 5. Primary spoken language

The category is the residents’ main everyday or home language. For multilingual residents, assign each person to the language they use most in everyday/home life when estimating shares.

### 6. Adult literacy rate

The percentage of residents aged 15 or older who can read and write a simple everyday statement with understanding, in any language, at the selected time. Use supported figures or a justified educated estimate, and record the basis. Use Unknown only when no estimate is justified; use not-applicable for an uninhabited location.

### 7. Political controller

For each land location and time, record the effective controlling entity by ID; when control is divided, choose the entity controlling the greatest area within the fixed boundary. States and local communities, tribes, or councils may be entities. Determine control from evidence about effective authority; use Unknown when no controller is supported by evidence or a justified estimate.

For joint administration, use a documented administrative lead. If none is documented, choose the entity with greater responsibility and resources when comparable evidence supports that distinction; use a stable entity ID to break remaining ties. At population zero, a location may have a controller, NoController, or Unknown. For populated locations, assign a supported controller or use Unknown. NoController means direct evidence or a justified estimate supports that no entity controls the location; Unknown means evidence is insufficient.

### Shared rules for attributes 8–9

Research both measures for the fixed location and selected year, using independently researched Population (#1). For compatible definitions, boundaries, and units, derive Total GDP as GDP per person × Population, or GDP per person as Total GDP ÷ Population. When both measures are supported by evidence or justified estimates, use the higher-confidence one and derive the other; when one is supportable, derive its counterpart; when neither is supportable, mark both Unknown. Retain all source evidence and the selection rationale.

### 8. GDP per person

Annual economic output per resident for the fixed location and selected year, in constant 2021 international dollars using GDP purchasing-power parity (GDP-PPP). Record source and estimate basis; document a compatible conversion when using older source measures.

### 9. Total GDP

Annual total economic output for the fixed location and selected year, in constant 2021 international dollars using GDP-PPP.

### 10. Median purchasing power

Annual person-weighted median disposable household income after taxes and transfers, adjusted for household size and prices. Express it in constant 2021 international dollars using consumption PPP. This represents typical resident purchasing power. Record evidence or estimate basis; use Unknown when no estimate is justified.

### 11. Infectious diseases and outbreaks

Record significant infectious diseases and outbreaks affecting a location and period; several may occur concurrently. Link disease and outbreak records with shared identities. A disease may be endemic and also have an outbreak. Record presence or absence using evidence or a justified estimate; mortality is researched separately and may be Unknown even when disease presence is known. Record source and estimate basis; use Unknown when research cannot justify a value.

### 12. Annual infectious-disease deaths

For each location and year, record annual resident deaths from the infectious diseases and outbreaks listed for that location and period in #11, using the same disease and outbreak identities. Research or estimate mortality separately from disease presence. Each disease count may be Unknown. Also record the combined count of unique people who died from those listed diseases, counting each person once after resolving duplicate reports within diseases and overlap across diseases. Use a supported count or justified estimate; mark the combined count Unknown when none is justified, while retaining individual estimates. Record sources, coverage, and overlap reasoning. Calculate percentages using Population (#1). Scope: infectious-disease deaths.

### 13. Vegetation

Assign one primary category to the whole land location at the selected time:

- **Forest:** dense tree cover, including jungle.
- **Woodland:** open tree cover with grass or shrubs between trees.
- **Shrubland:** bushes and shrubs dominate.
- **Grassland:** grasses dominate, including pasture.
- **Farmland:** cultivated crops, orchards, and plantations.
- **Sparse vegetation:** scattered plants with mostly exposed ground.
- **No vegetation:** essentially bare rock, sand, or permanent ice.
- **Unknown.**

### 14. Port functions

For each land location and selected time, record the set of active functions: Maritime, River, and Lake. Multiple functions may apply to one location. None means evidence or a justified estimate supports no active port function; Unknown means no defensible conclusion. Base each function on evidence of actual operation at that time. A maritime port may lie upriver. Record functions for the whole location.

### 15. Notable production

List the locally significant goods actually produced within the location at the selected time, using the shared product catalog. Multiple goods may apply; examples include agricultural products, extracted materials, livestock, fish, and timber. Record sources and estimate basis. None means evidence or a justified estimate supports no notable production; Unknown means the available research cannot establish it.

## Time-agnostic location attributes

### 1. Topography

Use one primary category for the whole land location: Flatland, Hills, Mountains, Plateau, or Unknown.

### 2. Water type

Use one primary type for each water location, based on its local setting: Open ocean, Coastal waters, Inland sea, Narrows, Lake, or Unknown. Inland sea is an enclosed or semi-enclosed marine basin. Narrows includes straits, narrow channels, and constrained archipelago waters. High-elevation lakes are classified as Lake.

### 3. Climate

Climate is a fixed present-day reference layer across the historical timeline. Use the published GloH2O Köppen–Geiger V3 historical raster for 1991–2020 as the working baseline; record its version and reference period. After geography is finalized, overlay the raster and assign each land location its largest-area class, checking coverage and coasts. This PR records the design; data import follows geography completion.

Use all 30 classes. Quantitative definitions govern classification; display familiar names while retaining underlying codes. Five broad climate families may be derived for display. Unknown is a separate value.

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

## Derived geographic relationships

After geography is finalized, derive adjacency from map-cell assignments and recompute it when geography changes. Two locations are neighbors when their cells share an edge. Store neighboring location IDs for every land and water location; corner contact alone is not adjacency.

Derive land-location access links from neighboring locations and finalized river overlays. Link lakes by neighboring Lake location IDs; derive a coastal-access Yes/No flag, if useful, from adjacent marine-water locations. Keep lake access separate from coastal access. Link rivers by river IDs where finalized river paths intersect or follow a location boundary. Rivers remain selectable overlays, not locations. These links represent geographic access.

## Political-entity attributes

### Shared entity record and identity

Each entity has a stable ID and start and end year; leave the end open for an entity that still exists. Controller references must fall within the entity’s lifetime. Identity follows political-state continuity: a change in ruler or government type alone leaves the ID unchanged, while distinct political states have distinct IDs even when they share a civilization or territory.

### Subordination relationship

Record subordinate and overlord entity IDs, start and end year, and evidence or estimate basis when one political entity holds superior political authority over another that retains its own government. The overlord relationship does not replace the local controller assigned to a location.

### Primary government type

Store one primary type per political entity and time; locations receive it through their controller. Choose the best-fitting category for the entity’s governing arrangement, using Unknown when no classification is justified.

- **Monarchy:** government organized around a monarch.
- **Republic:** political authority is exercised through civic institutions and public offices.
- **Theocracy:** religious authorities or institutions hold governing power.
- **Steppe horde:** a mobile steppe confederation organized around military and kinship leadership.
- **Tribal polity:** political authority is organized through tribal communities and leadership.
- **Military government:** military authorities directly govern.
- **One-party state:** one ruling party monopolizes political power.
- **Personalist dictatorship:** governing power is centered on an individual leader.

When categories overlap, select the best-fitting type as primary.

## Time-dependent trade relationships

Record significant directed connections between existing geographic units (location, province, area, region, subcontinent, or continent) or political entities. Endpoints may use different levels. Record from/to endpoints, active year or inclusive year span, one or more shared product IDs, transport by land, river, sea, or a known combination, and the evidence or estimate basis. These connections describe notable trade; a location may trade goods it does not produce locally.

Keep each connection at the geographic level supported by its evidence. A regional record does not imply known flows for its contained locations. Retain sources whose coverage does not sufficiently match an endpoint as evidence without assigning an exact endpoint quantity. Avoid summing regional totals together with contained detailed flows.

## App presentation and remaining design

Map and detail views use the same accepted data for the selected year. Time-dependent values follow that year; time-agnostic attributes remain fixed. Present estimates much like evidence-backed values in the clean primary view; show provenance, estimate basis, and uncertainty in details on demand. Trade and political relationship overlays appear in their respective map modes, not by default. The trade map lets users inspect a selected year and an endpoint’s partners and products.

Detailed database schema, indexes, and per-map-mode UI remain for later design. Existing geography UI decisions are unchanged.
