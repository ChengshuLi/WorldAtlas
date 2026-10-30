# Time-dependent attributes

Location attributes 1–10 apply to each fixed location at a selected time and do not change the geography. Political-entity attributes are stored per entity and linked through the location’s controller.

## Shared location-attribute applicability

Each location attribute declares whether it applies to land, water, or both. Attributes 1–10, including political controller, apply to land locations; water locations display Not applicable. The database rejects assignments to inapplicable types; display Not applicable separately from Unknown, which means insufficient evidence. Choose applicability individually for later attributes.

## 1. Population

Total residents within the location’s fixed boundary at the selected time, including all urban, suburban, and rural residents. Use supported counts or justified educated estimates, including zero; record the basis. Use Unknown only when no estimate is justified. Population is an independently researched input. Other attributes may use it, but it is never derived from them or changed to reconcile GDP or share data.

## 2. Location rank

Classify the whole location at the selected time as Uninhabited, Rural, Town, City, or Unknown, based on its historical character. Uninhabited means population zero; Rural covers inhabited non-urban locations, including nomadic populations. A location ranked Town or City may contain suburban areas or countryside within its boundary. Rank is not determined by total population: a City may have fewer residents than a Rural location. Unknown population does not require Unknown rank; use Unknown rank only when no classification can be justified.

## Shared rules for attributes 3–5

For each attribute, record the resident category with the largest population share at the selected time. The share need not exceed half. Use evidence or a justified educated estimate. Use Unknown only when no primary category can be justified, and Not applicable when population is zero. Record sources and estimate basis.

Optional share breakdowns use the same structure for all three: **complete** accounts for the population, **partial** records some shares, and **unavailable** means no shares can be justified. A partial or unavailable breakdown may not show which category is largest; a defensible estimate may still support a primary category. Retain supported or estimated shares with their basis.

## 3. Primary culture

The category is the resident cultural group.

## 4. Primary religion

The category is the resident religious affiliation; Unaffiliated is valid.

## 5. Primary spoken language

The category is the residents’ main everyday or home language. For multilingual residents, assign each person to the language they use most in everyday/home life when estimating shares.

## 6. Adult literacy rate

The percentage of residents aged 15 or older who can read and write a simple everyday statement with understanding, in any language, at the selected time. Use supported figures or a justified educated estimate, and record the basis. Use Unknown only when no estimate is justified; use not-applicable for an uninhabited location.

## 7. Political controller

For each land location and time, record the effective controlling entity by ID; when control is divided, choose the entity controlling the greatest area within the fixed boundary. States and local communities, tribes, or councils may be entities. Use Unknown when no controller is supported by evidence or a justified estimate. Population alone does not establish control.

For joint administration, use a documented administrative lead; otherwise, when comparable evidence supports it, use the entity with greater responsibility and resources. A stable entity ID breaks any remaining tie. At population zero, a location may have a controller, NoController, or Unknown. With positive population, record a controller or Unknown. NoController means direct evidence or a justified estimate supports that no entity controls the location; Unknown means evidence is insufficient.

## 8. GDP per person

Annual economic output per resident for the fixed location and selected year, in constant 2021 international dollars using GDP purchasing-power parity (GDP-PPP). Use supported figures or justified estimates, record the basis, and convert older source measures only with a documented compatible conversion. Use Unknown when no estimate is justified and not-applicable when population is zero.

## 9. Total GDP

For inhabited locations with positive population, display total GDP as GDP per person multiplied by selected population for the same location, year, and units. Retain directly reported total GDP as evidence, including to estimate GDP per person when definitions are compatible. When reported totals and per-person figures conflict, compare dates, boundaries, definitions, and units; choose the better-supported GDP evidence, keep population fixed, and record the rationale. GDP evidence never determines population.

## 10. Median purchasing power

Annual person-weighted median disposable household income after taxes and transfers, adjusted for household size and prices. Express it in constant 2021 international dollars using consumption PPP. This represents typical resident purchasing power. Record evidence or estimate basis; use Unknown when no estimate is justified and not-applicable for an uninhabited location.

Record sources and estimate basis for these values. Other attributes remain for later discussion.

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
