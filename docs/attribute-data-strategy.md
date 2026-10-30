# Attribute strategy

Location attributes may be time-dependent or time-agnostic. Political-entity government type is stored per entity and time; locations receive it through their controller.

## Shared location-attribute applicability

Each location attribute declares whether it applies to land, water, or both. Time-dependent location attributes 1–13, including political controller, apply to land. Among time-agnostic attributes, Topography and Climate apply to land, while Water type applies to water. Water locations show Not applicable for land-only attributes; attributes 8–10 also show Not applicable when population is zero. The database rejects incompatible assignments, and the UI distinguishes Not applicable from Unknown (insufficient evidence). Later attributes declare applicability individually.

## Time-dependent location attributes

### 1. Population

Total residents within the location’s fixed boundary at the selected time, including all urban, suburban, and rural residents. Use supported counts or justified educated estimates, including zero; record the basis. Use Unknown only when no estimate is justified. Population is an independently researched input. Other attributes may use it, but it is never derived from them or changed to reconcile GDP or share data.

### 2. Location rank

Classify the whole location at the selected time as Uninhabited, Rural, Town, City, or Unknown, based on its historical character. Uninhabited means population zero; Rural covers inhabited non-urban locations, including nomadic populations. A location ranked Town or City may contain suburban areas or countryside within its boundary. Rank is not determined by total population: a City may have fewer residents than a Rural location. Unknown population does not require Unknown rank; use Unknown rank only when no classification can be justified.

### Shared rules for attributes 3–5

For each attribute, record the resident category with the largest population share at the selected time. The share need not exceed half. Use evidence or a justified educated estimate. Use Unknown only when no primary category can be justified, and Not applicable when population is zero. Record sources and estimate basis.

Optional share breakdowns use the same structure for all three: **complete** accounts for the population, **partial** records some shares, and **unavailable** means no shares can be justified. A partial or unavailable breakdown may not show which category is largest; a defensible estimate may still support a primary category. Retain supported or estimated shares with their basis.

### 3. Primary culture

The category is the resident cultural group.

### 4. Primary religion

The category is the resident religious affiliation; Unaffiliated is valid.

### 5. Primary spoken language

The category is the residents’ main everyday or home language. For multilingual residents, assign each person to the language they use most in everyday/home life when estimating shares.

### 6. Adult literacy rate

The percentage of residents aged 15 or older who can read and write a simple everyday statement with understanding, in any language, at the selected time. Use supported figures or a justified educated estimate, and record the basis. Use Unknown only when no estimate is justified; use not-applicable for an uninhabited location.

### 7. Political controller

For each land location and time, record the effective controlling entity by ID; when control is divided, choose the entity controlling the greatest area within the fixed boundary. States and local communities, tribes, or councils may be entities. Use Unknown when no controller is supported by evidence or a justified estimate. Population alone does not establish control.

For joint administration, use a documented administrative lead; otherwise, when comparable evidence supports it, use the entity with greater responsibility and resources. A stable entity ID breaks any remaining tie. At population zero, a location may have a controller, NoController, or Unknown. With positive population, record a controller or Unknown. NoController means direct evidence or a justified estimate supports that no entity controls the location; Unknown means evidence is insufficient.

### 8. GDP per person

Annual economic output per resident for the fixed location and selected year, in constant 2021 international dollars using GDP purchasing-power parity (GDP-PPP). Use supported figures or justified estimates, record the basis, and convert older source measures only with a documented compatible conversion. Use Unknown when no estimate is justified.

### 9. Total GDP

Annual total economic output for the fixed location and selected year, in constant 2021 international dollars using GDP-PPP.

### Shared GDP calculation for attributes 8–9

Research both values, using selected population as an independently established input. For the same location, year, and boundary, with compatible definitions and units, calculate total GDP = GDP per person × population, or GDP per person = total GDP ÷ population. If both are supported by evidence or justified estimates, choose the higher-confidence value and derive the other. If only one is supportable, derive its counterpart; if neither is supportable, mark both Unknown. Retain all source evidence and the selection rationale.

### 10. Median purchasing power

Annual person-weighted median disposable household income after taxes and transfers, adjusted for household size and prices. Express it in constant 2021 international dollars using consumption PPP. This represents typical resident purchasing power. Record evidence or estimate basis; use Unknown when no estimate is justified.

### 11. Infectious diseases and outbreaks

Record significant infectious diseases and outbreaks affecting a location and period; several may occur concurrently. Link disease and outbreak records with shared identities. Endemic disease and an outbreak can overlap. Disease presence may be known while deaths remain Unknown. Use evidence or a justified estimate, with its basis; report absence only when supported, and use Unknown when research is missing.

### 12. Annual infectious-disease deaths

For each location and year, record annual resident deaths from the infectious diseases and outbreaks listed for that location and period in #11, using the same disease and outbreak identities. Research or estimate mortality separately; disease presence does not determine a death count, and mortality may be Unknown even when presence is known. Each disease count may be Unknown. Also record the combined count of unique people who died from those listed diseases. Consolidate overlapping reports within each disease and account for overlap across diseases; the combined count is not a raw sum. Use a supported count or justified estimate, otherwise mark the combined count Unknown while retaining individual estimates. Record sources, coverage, and overlap reasoning. Calculate percentages using Population (#1). This attribute covers infectious-disease deaths, not all-cause mortality; individual death registries are unnecessary.

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

Record sources and estimate basis for these time-dependent values; other attributes remain for later discussion.

## Time-agnostic location attributes

### 1. Topography

Use one primary category for the whole land location: Flatland, Hills, Mountains, Plateau, or Unknown.

### 2. Water type

Use one primary type for each water location, based on its local setting: Open ocean, Coastal waters, Inland sea, Narrows, Lake, or Unknown. Inland sea is an enclosed or semi-enclosed marine basin. Narrows includes straits, narrow channels, and constrained archipelago waters. High-elevation lakes are classified as Lake.

### 3. Climate

Climate is a fixed present-day reference layer across the historical timeline. Use the published GloH2O Köppen–Geiger V3 historical raster for 1991–2020 as the working baseline; record its version and reference period. After geography is finalized, overlay the raster and assign each land location its largest-area class, checking coverage and coasts. This PR records the design; data import follows geography completion.

Retain all 30 classes without rarity-based merging. Quantitative definitions govern classification; familiar names are displayed while the underlying codes are retained. Five broad climate families may be derived for display. Unknown is separate from the classes.

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

## Political-entity attributes

### Primary government type

Store one primary type per political entity and time; locations receive it through their controller. Choose the category that best describes the entity’s governing arrangement, even where descriptions overlap. Use Unknown when no classification is justified.

- **Monarchy:** government organized around a monarch.
- **Republic:** political authority is exercised through civic institutions and public offices.
- **Theocracy:** religious authorities or institutions hold governing power.
- **Steppe horde:** a mobile steppe confederation organized around military and kinship leadership.
- **Tribal polity:** political authority is organized through tribal communities and leadership.
- **Military government:** military authorities directly govern.
- **One-party state:** one ruling party monopolizes political power.
- **Personalist dictatorship:** governing power is centered on an individual leader.

A government may fit more than one description; store one primary type without imposing a fixed priority among categories.
