# Temporal import contract

Use `npm run data:import -- records.json`, then restart the server or rebuild the static export. Imports are atomic. Signed calendar years have no zero; starts are inclusive, ends exclusive. `2027` is the end sentinel for 2026. Year precision does not establish an exact day within a year.

## Identity and existence

Import geographic entities through `units` or polygon `locations` first. Their reference IDs and kinds enter `entities` automatically. An optional `entities` record specifies sourced `valid_from` / `valid_to` lifecycle bounds. Outside known bounds an entity is absent; unknown bounds do not infer founding or abandonment. Lifetimes describe that entity, not the earliest habitation of its land. Custom geographic entities must still have a complete reference chain.

Settlements use `entities` with `kind: "settlement"`, a stable `id`, reference `name`, and a location `parent_id`. They are associated records, not point replacements for polygon locations. Settlement rank and population remain separate from location attributes. A place name containing “city” does not establish a dated rank.

## Dated records

`entity_history` fields:

| Field | `value` | Meaning |
|---|---|---|
| `name` | Nonempty string | Preferred dated name or search alias |
| `parent` | Parent entity ID | Exactly the adjacent tier; settlement → location |
| `existence` | `exists`, `not_exists`, `unknown` | Explicit evidence about existence in an interval |
| `attributes` | Object | Complete nullable attribute snapshot, plus `habitation` |

All records need a unique `id`, `entity_id`, `valid_from`, `valid_to`, and `source`. `is_example` defaults to 0; illustrative records require 1. A field is not carried forward beyond its interval. Source-backed records outrank examples. Attribute snapshots omit unspecified values rather than inheriting them. Legacy `states` remain supported; generic location attributes take precedence within the same evidence class. Settlement attributes never implicitly become location attributes.

Names optionally specify `language` (default `und`) and `name_role` (`preferred`, default, or `alias`). Preferred names cannot overlap for the same entity, language and evidence class. Aliases may overlap and remain searchable across the timeline. Display prefers sourced English, then undetermined language, then other recorded languages. The title uses a supported historical name when available; otherwise it uses the recognizable reference name. Present-day reference is always shown separately, with name evidence in the collapsed section. Undated ancestor labels remain reference geography.

`habitation` accepts `inhabited`, `uninhabited`, or `unknown`. Explicit uninhabited records cannot simultaneously assign positive population or a settlement rank. Allowed ranks are `unsettled`, `rural settlement`, `town`, `city`, `metropolis`. Unsettled requires explicit sourced evidence of no inhabitants; modeled or rounded zero is insufficient. Missing rank remains unknown.

For example (entirely illustrative):

```json
{
  "entity_history": [{
    "id": "demo:name:1444", "entity_id": "atlas:city:GBR-Greater London",
    "field": "name", "value": "Example historical name", "language": "en",
    "valid_from": 1444, "valid_to": 1445,
    "source": "Illustrative import, not historical evidence", "is_example": 1
  }]
}
```

Dated parent records change geographic membership and borders. Imports reject skipped levels and absent parents at interval transitions. Reference membership outside a dated interval is visibly marked reference, not an assertion of ancient administration. Political ownership is an attribute and does not automatically rewrite geographic membership.

## Boundaries, splits and mergers

A rename retains the same entity ID. A genuinely new administrative or settlement entity receives a new ID. `entity_links` records need `id`, `predecessor_id`, `successor_id`, `kind: successor | split | merge`, `year`, `source`, and optional `is_example`. A split has multiple links from one predecessor; a merger has multiple links into one successor. End predecessor lifetimes and begin successors using separately sourced lifecycle records. Links alone do not establish dates of existence or manufacture geometry.

Location `boundaries` records provide dated polygon overrides. A changed footprint can retain an ID if it is still the same entity. Higher polygons/borders follow their location members. The fixed grid is rasterized again when boundaries or membership change. Imports validate GeoJSON structure; **validate imported replacement geometries together in GIS** for self-intersection, overlap and coverage. Defensive pixel tie-breaking is not historical research.

Reference-data migrations can archive superseded source IDs while preserving their states and boundaries. Those archived records are not automatically mapped onto finer successors: doing so would invent their historical extent or distribute demographic totals without evidence.
