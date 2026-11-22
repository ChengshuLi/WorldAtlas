"""Describe the geographic records and source catalog saved with a map build."""

from typing import Literal, TypedDict

from pydantic import JsonValue

from worldatlas.geodesy.geojson import GeoJSONGeometry

type PhysicalClass = Literal["land", "water"]
type EligibleClass = Literal["land", "water", "mixed"]
type RuleOperation = Literal[
    "assign_area",
    "divide_area",
    "nearest_land",
    "nearest_coastal_water",
    "nearest_basin_water",
    "nearest_water",
]
type RuleFeatureRole = Literal[
    "boundary_line",
    "scope_area",
    "scope_component",
    "distance_reference",
    "connected_to",
]


class GeographicLevel(TypedDict):
    """Name one hierarchy level and its allowed parent level."""

    id: str
    parent_id: str | None


class GeographicEntity(TypedDict):
    """Record a geographic entity, its actual parent, and its display color."""

    id: int
    name: str
    level_id: str
    parent_id: int | None
    physical_class: EligibleClass
    color_rgb: str | None


class EntityColor(TypedDict):
    """Pair a geographic entity ID with its saved display color."""

    entity_id: int
    color_rgb: str | None


class MapCodeBinding(TypedDict):
    """Name the entity and physical class represented by one map code."""

    code: int
    entity_id: int
    physical_class: PhysicalClass


class GeographicRule(TypedDict):
    """Describe an assignment operation for one geographic parent."""

    id: str
    parent_id: int
    operation: RuleOperation
    physical_class: EligibleClass
    unit: Literal["cell", "component"]
    unassigned_only: bool
    rationale: str


class RuleFeature(TypedDict):
    """Link a rule to the imported feature used in a particular role."""

    rule_id: str
    feature_id: str
    role: RuleFeatureRole


class RuleTarget(TypedDict):
    """Link a rule to an eligible child and, for divisions, its label point."""

    id: str
    rule_id: str
    entity_id: int
    label_point_id: str | None


class FeatureReference(TypedDict):
    """Identify a feature and the construction that produced it."""

    id: str
    construction_id: str


class GeographicFeature(FeatureReference):
    """Hold an imported feature and its exact WGS84 GeoJSON geometry."""

    geometry: GeoJSONGeometry


class SourceReference(TypedDict):
    """Identify one file by its source catalog ID."""

    source_id: str


class RuleSource(SourceReference):
    """Record a supporting citation for a geographic rule."""

    rule_id: str
    citation_section: str
    interpretation: str


class ConstructionSource(SourceReference):
    """Link a construction to a raw source it references."""

    construction_id: str


class SourceAsset(SourceReference):
    """Record an archived raw file's location, metadata, and byte identity."""

    title: str
    provider: str
    source_uri: str
    license_name: str
    license_uri: str
    attribution: str
    r2_bucket: str
    r2_key: str
    sha256: str
    size_bytes: int


class ConstructionRecord(TypedDict):
    """Record an import method, its recipe arguments, and its reasoning."""

    id: str
    method: str
    arguments: dict[str, JsonValue]
    basis: str


class GeographicSelection[Feature = GeographicFeature](TypedDict):
    """Hold the selected divisions, their geometry, and supporting records.

    The SQL export starts with feature references. The saved selection uses
    complete features after their geometry has been read.
    """

    schema: Literal["worldatlas-geographic-division-v2"]
    levels: list[GeographicLevel]
    entities: list[GeographicEntity]
    category_bindings: list[MapCodeBinding]
    rules: list[GeographicRule]
    rule_features: list[RuleFeature]
    rule_targets: list[RuleTarget]
    rule_sources: list[RuleSource]
    features: list[Feature]
    construction_sources: list[ConstructionSource]
    sources: list[SourceReference]


class BuildSelection(TypedDict):
    """Hold the complete frozen JSON inputs to a map build."""

    schema: Literal["worldatlas-input-selection-v4"]
    selected_at: str
    geography: GeographicSelection
    construction_records: list[ConstructionRecord]
    raw_sources: list[SourceAsset]
