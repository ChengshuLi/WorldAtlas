"""Small current-grid fixtures check source-neutral land selection and composition."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import patch_rows, write_layer
from worldatlas.map_build.core.rle import open_grid
from worldatlas.map_build.land.geographic_assignments import resolve_assignments
from worldatlas.map_build.land.components import ComponentGrid
from worldatlas.map_build.land.composition import compose_land
from worldatlas.map_build.land.regional import build_regional
from worldatlas.map_build.land.partitions import build_partitions, resolve_component_partitions
from worldatlas.map_build.water.shared_nearest import crop


def feature(ident, geometry, reference="OGC:CRS84"):
    checksum = hashlib.sha256(
        json.dumps(geometry, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return dict(
        feature_id=ident,
        geometry=geometry,
        geometry_sha256=checksum,
        coordinate_reference=reference,
    )


def polygon(west, south, east, north):
    return {
        "type": "Polygon",
        "coordinates": [
            [[west, south], [east, south], [east, north], [west, north], [west, south]]
        ],
    }


class RegionalTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.grid = Grid(8, 4, 45.0)
        self.physical = np.ones((4, 8), dtype=np.uint32)
        self.physical[1, [1, 2, 5]] = self.physical[2, [0, 7]] = 17
        self.baseline = np.where(self.physical == 17, 301, 0).astype(np.uint32)
        for name, values in [("physical", self.physical), ("baseline", self.baseline)]:
            write_layer(
                self.root / name,
                self.grid,
                patch_rows(values, self.grid.bounds, self.grid),
            )
        components = self.root / "components"
        components.mkdir()
        np.array([0, 0, 2, 4, 4], dtype="<u4").tofile(components / "rows.u32le")
        np.array(
            [[1, 3, 7], [5, 6, 90000], [0, 1, 42], [7, 8, 42]], dtype="<u4"
        ).tofile(components / "runs.u32le")
        self.bindings = [
            dict(entity_id=81, physical_class="land", code=301),
            dict(entity_id=42, physical_class="land", code=999),
        ]
        self.features = [
            feature("left", polygon(-130, 0, -50, 45)),
            feature("partial", polygon(-100, 0, -50, 45)),
            feature("right", {"type": "Point", "coordinates": [67.5, 22.5]}),
        ]
        self.rules = [
            dict(
                assignment_id="left",
                entity_id=81,
                selection=dict(feature_ids=["left"], relation="contains_component"),
            ),
            dict(
                assignment_id="right",
                entity_id=42,
                selection=dict(feature_ids=["right"], relation="point_component"),
            ),
        ]

    def components(self):
        return ComponentGrid(
            self.root / "physical", self.root / "components", self.grid
        )

    def test_complete_structured_geometry_to_final_land(self):
        selection = {
            "domains": {
                "regional": dict(
                    features=self.features,
                    assignments=self.rules,
                    category_bindings=self.bindings,
                )
            }
        }
        report = build_regional(
            selection,
            self.grid,
            self.root / "physical",
            self.root / "components",
            self.root / "baseline",
            self.root / "result",
        )
        self.assertEqual(report["claims"][0]["component_ids"], [7])
        self.assertEqual(report["claims"][1]["component_ids"], [90000])
        self.assertEqual(report["counts"], {"301": 4, "999": 1})
        with open_grid(report["land"], self.grid) as output:
            self.assertEqual(
                crop(*output, 1, 0, 8, 8).tolist(), [0, 301, 301, 0, 0, 999, 0, 0]
            )

    def test_single_condition_shape_and_references_are_checked(self):
        from copy import deepcopy

        for value in (
            [],
            {},
            {"relation": "point_component"},
            {"relation": "unknown", "feature_id": "right"},
            {"relation": "point_component", "feature_id": " "},
            {"relation": "point_component", "feature_id": "right", "combine": "all"},
        ):
            rules = deepcopy(self.rules)
            rules[0]["selection"] = value
            with (
                self.components() as components,
                self.assertRaisesRegex(ValueError, "exactly one"),
            ):
                resolve_assignments(rules, self.features, components, self.bindings)
        missing = dict(
            assignment_id="missing",
            entity_id=81,
            selection=dict(relation="point_component", feature_id="absent"),
        )
        with (
            self.components() as components,
            self.assertRaisesRegex(ValueError, "missing feature"),
        ):
            resolve_assignments([missing], self.features, components, self.bindings)

    def test_independent_assignment_rows_and_archived_union_have_the_same_result(self):
        current = [
            self.rules[0],
            dict(
                assignment_id="right",
                entity_id=81,
                selection=dict(feature_ids=["right"], relation="point_component"),
            ),
        ]
        archived = [
            dict(
                affiliation_id="old",
                entity_id=81,
                component_selection=dict(
                    combine="any",
                    conditions=[
                        dict(
                            relation=r["selection"]["relation"],
                            feature_id=r["selection"]["feature_ids"][0],
                        )
                        for r in current
                    ],
                ),
            )
        ]
        with self.components() as components:
            a = resolve_assignments(current, self.features, components, self.bindings)
            b = resolve_assignments(archived, self.features, components, self.bindings)
        self.assertEqual(a["component_entities"], b["component_entities"])
        self.assertEqual([r["assignment_id"] for r in a["claims"]], ["left", "right"])
        self.assertEqual(b["claims"][0]["affiliation_id"], "old")

    def test_grouped_polygons_are_unioned_before_component_coverage(self):
        pieces = [
            feature("first", polygon(-130, 0, -90, 45)),
            feature("second", polygon(-85, 0, -50, 45)),
        ]
        for relation in ("contains_component", "majority_component"):
            rule = dict(
                assignment_id="group",
                entity_id=81,
                selection=dict(relation=relation, feature_ids=["first", "second"]),
            )
            with self.components() as components:
                result = resolve_assignments([rule], pieces, components, self.bindings)
                self.assertEqual(result["component_entities"], {7: 81})
        # Repeated coverage from distinct features must not be counted twice.
        pieces[1] = feature("second", pieces[0]["geometry"])
        with (
            self.components() as components,
            self.assertRaisesRegex(ValueError, "no current land"),
        ):
            resolve_assignments([rule], pieces, components, self.bindings)

    def test_grouped_points_and_dateline_polygons(self):
        points = [
            self.features[2],
            feature("left-point", {"type": "Point", "coordinates": [-112.5, 22.5]}),
        ]
        rule = dict(
            assignment_id="group",
            entity_id=81,
            selection=dict(
                relation="point_component", feature_ids=["right", "left-point"]
            ),
        )
        with self.components() as components:
            result = resolve_assignments([rule], points, components, self.bindings)
            self.assertEqual(result["component_entities"], {7: 81, 90000: 81})
        areas = [
            feature("west", polygon(-180, -45, -135, 0)),
            feature("east", polygon(135, -45, 180, 0)),
        ]
        rule["selection"] = dict(
            relation="contains_component", feature_ids=["west", "east"]
        )
        with self.components() as components:
            result = resolve_assignments([rule], areas, components, self.bindings)
            self.assertEqual(result["component_entities"], {42: 81})

    def test_grouped_selection_rejects_malformed_ids_and_geometry_types(self):
        for ids in ([], "left", [None], [7], [" "], ["left", "left"]):
            rule = dict(
                assignment_id="group",
                entity_id=81,
                selection=dict(relation="contains_component", feature_ids=ids),
            )
            with (
                self.subTest(ids=ids),
                self.components() as components,
                self.assertRaisesRegex(ValueError, "distinct nonempty"),
            ):
                resolve_assignments([rule], self.features, components, self.bindings)
        for relation in ("contains_component", "point_component"):
            rule["selection"] = dict(relation=relation, feature_ids=["left", "right"])
            with (
                self.components() as components,
                self.assertRaisesRegex(ValueError, "selection needs"),
            ):
                resolve_assignments([rule], self.features, components, self.bindings)

    def test_current_assignments_have_feature_ids_and_fixed_majority_matching(self):
        rule = dict(assignment_id="current", entity_id=81, feature_ids=["left"])
        with self.components() as components:
            result = resolve_assignments(
                [rule], self.features, components, self.bindings
            )
            self.assertEqual(result["component_entities"], {7: 81})
        for ids in ([], ["left", "left"], [None], [" "]):
            rule["feature_ids"] = ids
            with (
                self.subTest(ids=ids),
                self.components() as components,
                self.assertRaises(ValueError),
            ):
                resolve_assignments([rule], self.features, components, self.bindings)

    def test_single_feature_frozen_assignment_replays_without_mutation(self):
        rule = dict(
            assignment_id="frozen",
            entity_id=81,
            selection=dict(relation="contains_component", feature_id="left"),
        )
        original = json.dumps(rule, sort_keys=True)
        with self.components() as components:
            result = resolve_assignments(
                [rule], self.features, components, self.bindings
            )
        self.assertEqual(result["component_entities"], {7: 81})
        self.assertEqual(json.dumps(rule, sort_keys=True), original)

    def test_contains_does_not_assign_a_partial_component_and_overlap_can_select_it(
        self,
    ):
        rule = dict(
            assignment_id="partial",
            entity_id=81,
            selection=dict(feature_id="partial", relation="contains_component"),
        )
        with self.components() as components:
            with self.assertRaisesRegex(ValueError, "no current land components"):
                resolve_assignments([rule], self.features, components, self.bindings)
            rule["selection"]["relation"] = "intersects_component"
            self.assertEqual(
                resolve_assignments([rule], self.features, components, self.bindings)[
                    "component_entities"
                ],
                {7: 81},
            )

    def test_numbered_report_uses_exact_cell_runs_and_detects_overlap(self):
        from worldatlas.map_build.land.assignment_report import write_report

        rules = [*self.rules, dict(self.rules[0], assignment_id="duplicate")]
        current = dict(
            domains=dict(
                regional=dict(
                    features=self.features,
                    assignments=rules,
                    category_bindings=self.bindings,
                    entities=[
                        dict(id=81, name="First", color_rgb="#123456"),
                        dict(id=42, name="Second", color_rgb="#654321"),
                    ],
                )
            )
        )
        with self.components() as components:
            result = write_report(current, components, self.root / "review")
        self.assertEqual([r["number"] for r in result["rules"]], [1, 2, 3])
        self.assertEqual([r["cell_count"] for r in result["rules"]], [2, 1, 2])
        self.assertEqual([r["feature_count"] for r in result["rules"]], [1, 1, 1])
        self.assertEqual(
            [r["unique_component_count"] for r in result["rules"]], [0, 1, 0]
        )
        self.assertEqual(result["rules"][0]["other_assignments"], ["duplicate"])
        self.assertTrue((self.root / "review/current/001.html").is_file())
        self.assertTrue((self.root / "review/index.html").is_file())

    def test_partial_coverage_wrapping_and_native_point_queries(self):
        with self.components() as components:
            self.assertEqual(components.totals(), {7: 2, 42: 2, 90000: 1})
            self.assertEqual(components.profile(self.features[1]["geometry"]), {7: 1})
            self.assertEqual(components.point(67.5, 22.5), 90000)
            wrapped = {
                "type": "MultiPolygon",
                "coordinates": [
                    polygon(-180, -45, -135, 0)["coordinates"],
                    polygon(135, -45, 180, 0)["coordinates"],
                ],
            }
            self.assertEqual(components.profile(wrapped), {42: 2})
            with self.assertRaisesRegex(ValueError, "physical land"):
                components.point(112.5, 22.5)
            with self.assertRaisesRegex(ValueError, "grid edge"):
                components.point(90, 22.5)

    def test_component_profile_ignores_water_boundary_contacts_but_rejects_land_ties(
        self,
    ):
        with self.components() as components:
            self.assertEqual(components.profile(polygon(-22.5, -45, 45, 45)), {})
            with self.assertRaisesRegex(ValueError, "cell center"):
                components.profile(polygon(-67.5, -45, 45, 45))

    def test_majority_matching_selects_whole_islands_without_selecting_large_neighbors(
        self,
    ):
        self.physical[1, 3] = 17
        write_layer(
            self.root / "three-cell-physical",
            self.grid,
            patch_rows(self.physical, self.grid.bounds, self.grid),
        )
        runs = np.fromfile(self.root / "components/runs.u32le", dtype="<u4").reshape(
            -1, 3
        )
        runs[0, 1] = 4
        runs.tofile(self.root / "components/runs.u32le")
        area = feature("most", polygon(-90, 0, 0, 45))
        rule = dict(
            assignment_id="group",
            entity_id=81,
            selection=dict(feature_id="most", relation="majority_component"),
        )
        with ComponentGrid(
            self.root / "three-cell-physical", self.root / "components", self.grid
        ) as components:
            result = resolve_assignments([rule], [area], components, self.bindings)
            self.assertEqual(result["component_entities"], {7: 81})
            rule["selection"]["relation"] = "contains_component"
            with self.assertRaisesRegex(ValueError, "no current"):
                resolve_assignments([rule], [area], components, self.bindings)
        runs[0, 1] = 3
        runs.tofile(self.root / "components/runs.u32le")
        rule["selection"] = dict(feature_id="partial", relation="majority_component")
        with (
            self.components() as components,
            self.assertRaisesRegex(ValueError, "no current"),
        ):
            resolve_assignments([rule], self.features, components, self.bindings)

    def test_scoped_partition_is_composed_once_and_cannot_change_water(self):
        partition = dict(
            geometry=polygon(-180, -45, -135, 0), entity_id=42, component_ids={42}
        )
        with self.components() as components:
            compose_land(
                components,
                self.root / "baseline",
                {90000: 42},
                self.bindings,
                self.root / "partitioned",
                partitions=[partition],
            )
        with open_grid(self.root / "partitioned", self.grid) as data:
            self.assertEqual(
                crop(*data, 2, 0, 8, 8).tolist(), [999, 0, 0, 0, 0, 0, 0, 301]
            )
        with (
            self.components() as components,
            self.assertRaisesRegex(ValueError, "conflicting"),
        ):
            compose_land(
                components,
                self.root / "baseline",
                {42: 81},
                self.bindings,
                self.root / "conflict",
                partitions=[partition],
            )

    def test_partition_contacts_on_water_are_irrelevant_but_land_ties_fail(self):
        partition = dict(geometry=polygon(-22.5, -45, 45, 45), entity_id=42)
        with self.components() as components:
            compose_land(
                components,
                self.root / "baseline",
                {},
                self.bindings,
                self.root / "water-contact",
                partitions=[partition],
            )
        partition["geometry"] = polygon(-67.5, -45, 45, 45)
        with (
            self.components() as components,
            self.assertRaisesRegex(ValueError, "cell center"),
        ):
            compose_land(
                components,
                self.root / "baseline",
                {},
                self.bindings,
                self.root / "land-contact",
                partitions=[partition],
            )

    def test_geographic_partition_overrides_distance_default_but_not_an_explicit_claim(
        self,
    ):
        seed = self.baseline.copy()
        seed[2, [0, 7]] = 0
        write_layer(
            self.root / "seeds",
            self.grid,
            patch_rows(seed, self.grid.bounds, self.grid),
        )
        partition = dict(geometry=polygon(-180, -45, -135, 0), entity_id=42)
        with self.components() as components:
            compose_land(
                components,
                self.root / "seeds",
                {},
                self.bindings,
                self.root / "defaults",
                component_defaults={42: 81},
                partitions=[partition],
            )
        with open_grid(self.root / "defaults", self.grid) as output:
            self.assertEqual(
                crop(*output, 2, 0, 8, 8).tolist(), [999, 0, 0, 0, 0, 0, 0, 301]
            )
        with (
            self.components() as components,
            self.assertRaisesRegex(ValueError, "conflicting"),
        ):
            compose_land(
                components,
                self.root / "seeds",
                {42: 81},
                self.bindings,
                self.root / "explicit-conflict",
                component_defaults={42: 81},
                partitions=[partition],
            )

    def component_partition(self):
        return dict(id='divider', feature_id='divider', bounds_lon_lat=[-130, -44, 130, 44],
                    side_a_entity_id=81, side_a_witness=[-60, 10],
                    side_b_entity_id=42, side_b_witness=[60, 10], rationale='Selected divide')

    def test_whole_component_partition_uses_entities_and_preserves_physical_water(self):
        line = feature('divider', dict(type='LineString', coordinates=[[0,80],[0,-80]]))
        domain = dict(features=[*self.features,line], assignments=[], category_bindings=self.bindings,
                      partitions=[self.component_partition()])
        result = build_regional(dict(domains={'regional':domain}), self.grid,
                                self.root/'physical', self.root/'components', self.root/'baseline',
                                self.root/'partitioned')
        self.assertEqual(result['counts'], {'301':4, '999':1})
        self.assertEqual(result['partitions'][0]['component_entities'], {7:81,90000:42})

    def test_component_partition_reports_scope_edges_and_rejects_land_crossings(self):
        line = feature('divider', dict(type='LineString', coordinates=[[-90,80],[-90,-80]]))
        record = self.component_partition()
        record['side_a_witness'] = [-110,10]
        with self.components() as components:
            with self.assertRaisesRegex(ValueError, 'crosses land component 7'):
                resolve_component_partitions([record], [line], components, self.bindings)
            protected = resolve_component_partitions([record], [line], components,
                                                     self.bindings, protected=[7])
            self.assertNotIn(7, protected['component_entities'])
            record['bounds_lon_lat'][0] = -100
            record['side_a_witness'] = [-95,10]
            result = resolve_component_partitions([record], [line], components, self.bindings)
            self.assertEqual(result['claims'][0]['scope_edge_components'], [7])
            self.assertNotIn(7, result['component_entities'])

    def test_opposing_partition_claims_are_rejected(self):
        line = feature('divider', dict(type='LineString', coordinates=[[0,80],[0,-80]]))
        a = self.component_partition()
        b = dict(a, id='opposite', side_a_entity_id=42, side_b_entity_id=81)
        with self.components() as components, self.assertRaisesRegex(ValueError, 'different entities'):
            resolve_component_partitions([a,b], [line], components, self.bindings)

    def test_selected_lines_produce_two_witnessed_partition_faces(self):
        a = feature("a", {"type": "LineString", "coordinates": [[0, 80], [0, 0]]})
        b = feature("b", {"type": "LineString", "coordinates": [[0, 0], [0, -80]]})
        a["boundary_id"], b["route_id"] = "a", "b"
        definition = dict(
            bounds_lon_lat=[-120, -40, 120, 40],
            sections=[dict(kind="boundary", id="a"), dict(kind="route", id="b")],
            sides=[
                dict(coordinates=[-60, 10], entity_id=81),
                dict(coordinates=[60, 10], entity_id=42),
            ],
        )
        domain = dict(
            mainland_boundaries=[a],
            routes=[b],
            policies=[
                dict(id="scope", kind="scoped_land_partition", definition=definition)
            ],
        )
        partitions = build_partitions(domain)
        from shapely.geometry import Point, shape

        self.assertTrue(shape(partitions[0]["geometry"]).contains(Point(-60, 10)))
        self.assertTrue(shape(partitions[1]["geometry"]).contains(Point(60, 10)))
        definition["sides"][1]["coordinates"] = [-30, 10]
        with self.assertRaisesRegex(ValueError, "opposite"):
            build_partitions(domain)
        definition["sides"][1]["coordinates"] = [60, 10]
        b["geometry"]["coordinates"][0] = [1, 0]
        b["geometry_sha256"] = feature("b", b["geometry"])["geometry_sha256"]
        with self.assertRaisesRegex(ValueError, "do not join"):
            build_partitions(domain)

    def test_projected_source_contact_uses_declared_operations_and_reports_unknown(
        self,
    ):
        from pyproj import Transformer
        from shapely.geometry import mapping, shape
        from shapely.ops import transform

        forward = Transformer.from_crs("OGC:CRS84", "EPSG:3857", always_xy=True)
        geometry = mapping(
            transform(forward.transform, shape(polygon(-130, 0, -50, 45)))
        )
        pipeline = Transformer.from_crs(
            "EPSG:3857", "OGC:CRS84", always_xy=True
        ).to_proj4()
        operation = dict(
            id="native",
            pipeline=pipeline,
            area_bounds=dict(west=-180, east=180, south=-85, north=85),
        )
        operations = dict(operations=[operation], operation_preference=["native"])
        with self.components() as components:
            counts = components.profile_projected(geometry, operations, {7, 90000})
            self.assertEqual(counts[7], dict(inside=2, boundary=0, unknown=0))
            self.assertEqual(counts[90000], dict(inside=0, boundary=0, unknown=0))
            operation["area_bounds"].update(west=-130, east=-50)
            self.assertEqual(
                components.profile_projected(geometry, operations, {90000})[90000][
                    "unknown"
                ],
                1,
            )

    def test_conflicting_targets_protected_components_and_bad_streams_fail(self):
        with self.components() as components:
            rules = [
                self.rules[0],
                dict(self.rules[0], assignment_id="other", entity_id=42),
            ]
            with self.assertRaisesRegex(ValueError, "different entities"):
                resolve_assignments(rules, self.features, components, self.bindings)
            with self.assertRaisesRegex(ValueError, "protected"):
                resolve_assignments(
                    self.rules, self.features, components, self.bindings, protected={7}
                )
        path = self.root / "components/runs.u32le"
        values = np.fromfile(path, dtype="<u4")
        values[0] = 0
        values.tofile(path)
        with (
            self.components() as components,
            self.assertRaisesRegex(ValueError, "coverage"),
        ):
            components.row(1)


if __name__ == "__main__":
    unittest.main()
