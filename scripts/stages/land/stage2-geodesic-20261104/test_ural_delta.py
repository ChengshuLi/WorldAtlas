import unittest

import ural_delta


def _line(points):
    return {"type": "LineString", "coordinates": points}


class UralDeltaTest(unittest.TestCase):
    def test_witness_sides_and_fail_closed_edges(self):
        bounds = [-130, 30, 40, 80]
        line, europe_ring, asia_ring = ural_delta.split_scope(
            [[-50, 90], [-60, 40], [-130, 40]], bounds, [-100, 60], [20, 60])
        rule = {
            "schema": ural_delta.SCHEMA,
            "scope_bounds": bounds,
            "line_scope_vertices": line,
            "europe_ring": europe_ring,
            "asia_ring": asia_ring,
            "europe_code": 19,
            "asia_code": 18,
        }
        self.assertEqual(ural_delta.classify_cell(rule, -100, 60), 19)
        self.assertEqual(ural_delta.classify_cell(rule, 20, 60), 18)
        self.assertIsNone(ural_delta.classify_cell(rule, 100, 60))
        with self.assertRaisesRegex(ValueError, "divider"):
            ural_delta.classify_cell(rule, -58, 50)
        with self.assertRaisesRegex(ValueError, "scope edge"):
            ural_delta.classify_cell(rule, -130, 60)

    def test_compiles_against_selected_boundary_and_closure(self):
        revision = "test-revision"
        boundary = _line([[51.8, 47.3], [51.8, 46.8]])
        route = _line([[51.8, 46.8], [51.7, 46.8], [51.0, 46.8]])
        snapshot = {
            "decision_revision": {"id": revision},
            "land_baseline_policy": {
                "decision_revision": revision,
                "boundary_ids": [ural_delta.BOUNDARY_ID],
                "route_ids": [ural_delta.ROUTE_ID],
            },
            "mainland_boundaries": [{
                "boundary_id": ural_delta.BOUNDARY_ID,
                "decision_revision": revision,
                "execution_status": "selected_for_research",
                "geometry": boundary,
                "geometry_sha256": ural_delta._geometry_hash(boundary),
            }],
            "routes": [{
                "route_id": ural_delta.ROUTE_ID,
                "decision_revision": revision,
                "execution_status": "selected_for_research",
                "geometry": route,
                "geometry_sha256": ural_delta._geometry_hash(route),
                "start_terminal": {"boundary_id": ural_delta.BOUNDARY_ID, "endpoint": "end"},
            }],
        }
        rule = ural_delta.compile_rule(snapshot, {18: "Asia", 19: "Europe"}, {
            "width": 131072, "height": 54614, "west": -180,
            "north": 90, "step": 360 / 131072,
        })
        self.assertEqual(rule["revision"], revision)
        self.assertEqual(rule["boundary_sha256"], snapshot["mainland_boundaries"][0]["geometry_sha256"])
        self.assertEqual(rule["route_sha256"], snapshot["routes"][0]["geometry_sha256"])
        self.assertEqual(rule["europe_code"], 19)
        self.assertEqual(rule["asia_code"], 18)
        self.assertEqual(rule["line_scope_vertices"][0][1], 47.24)
        self.assertEqual(rule["line_scope_vertices"][-1][0], 51.3)

    def test_rejects_bad_geometry_hash_or_missing_selection(self):
        with self.assertRaisesRegex(ValueError, "selected Ural boundary or closure route missing"):
            ural_delta.compile_rule({"decision_revision": {"id": "r"}, "land_baseline_policy": {"decision_revision": "r"}}, {18: "Asia", 19: "Europe"}, {})


if __name__ == "__main__":
    unittest.main()
