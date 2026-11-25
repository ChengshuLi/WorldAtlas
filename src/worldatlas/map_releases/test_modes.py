"""Verify edge adjacency, color choices, and the lookup for each actual level."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import write_layer
from worldatlas.map_build.test_support import selection
from worldatlas.map_releases.colors import (
    choose_muted_land_color,
    color_land,
    muted_color_samples,
    oklab,
)
from worldatlas.map_releases.modes import build_map_modes, land_code_neighbors, nearby_land_pairs


FILL_COLORS = (60, 98, 120), (227, 222, 210)


class PaletteTests(TestCase):
    def test_choice_maximizes_the_separation_from_its_closest_color(self):
        neighbor = (201, 111, 98)
        chosen = choose_muted_land_color({neighbor}, FILL_COLORS)
        candidates, lab = muted_color_samples()
        possible = [i for i, color in enumerate(candidates) if color not in (neighbor, *FILL_COLORS)]
        references = oklab([neighbor, *FILL_COLORS])
        distances = np.linalg.norm(lab[:, None] - references, axis=2).min(axis=1)
        self.assertEqual(chosen, candidates[max(possible, key=lambda i: distances[i])])

    def test_coloring_preserves_authored_colors_and_rejects_conflicting_borders(self):
        fixed = (201, 111, 98)
        graph = {1: {2}, 2: {1}, 3: set()}
        colors = color_land(graph, {1: fixed}, FILL_COLORS)
        self.assertEqual(colors[1], fixed)
        self.assertNotEqual(colors[2], fixed)
        self.assertEqual(colors[3], choose_muted_land_color(set(), FILL_COLORS))
        with self.assertRaisesRegex(ValueError, "entities 1 and 2 share"):
            color_land(graph, {1: fixed, 2: fixed}, FILL_COLORS)

    def test_many_adjacent_entities_use_distinct_generated_colors(self):
        ids = set(range(10))
        graph = {entity: ids - {entity} for entity in ids}
        colors = color_land(graph, {}, FILL_COLORS)
        self.assertEqual(len(set(colors.values())), len(graph))
        self.assertFalse(set(colors.values()).intersection(FILL_COLORS))
        reverse = dict(reversed(list(graph.items())))
        self.assertEqual(color_land(reverse, {}, FILL_COLORS), colors)

    def test_an_exhausted_palette_reports_the_conflict(self):
        color = (201, 111, 98)
        with patch("worldatlas.map_releases.colors.muted_color_samples",
                   return_value=((color,), oklab([color]))):
            with self.assertRaisesRegex(ValueError, "ran out of distinct muted land colors"):
                choose_muted_land_color({color}, FILL_COLORS)


class ModeTests(TestCase):
    def test_only_land_edges_contribute_including_at_the_dateline(self):
        grid = Grid(8, 4, 45)
        with TemporaryDirectory() as folder:
            path = Path(folder) / "grid"
            write_layer(path, grid, [
                (0, [(0, 1, 10), (1, 2, 20), (2, 7, 9), (7, 8, 0xFFFFFFFF)]),
                (1, [(0, 1, 30), (1, 8, 9)]),
            ])
            self.assertEqual(land_code_neighbors(path, grid, []), set())
            self.assertEqual(land_code_neighbors(path, grid, [10, 20, 30, 0xFFFFFFFF]), {(10, 20), (10, 30), (10, 0xFFFFFFFF)})

    def test_neighbors_across_water_follow_the_same_color_rule_as_shared_edges(self):
        grid = Grid(1440, 9, 0.25)
        geography = selection()["geography"]
        geography["levels"].append(dict(id="continent", parent_id="world"))
        codes = (10, 20, 30)
        for entity_id in codes:
            geography["entities"].append(dict(
                id=entity_id, level_id="continent", parent_id=0, name=str(entity_id),
                color_rgb="#C96F62", physical_class="land",
            ))
            geography["category_bindings"].append(dict(
                code=entity_id, entity_id=entity_id, physical_class="land",
            ))
        with TemporaryDirectory() as folder:
            path = Path(folder) / "grid"
            report = write_layer(path, grid, [
                (3, [(0, 2, 10), (2, 4, 9), (4, 6, 20)]),
                (8, [(0, 2, 10), (2, 4, 30)]),
            ])
            self.assertEqual(land_code_neighbors(path, grid, codes), {(10, 30), (10, 20)})

            def build_modes():
                return build_map_modes(path, grid, geography, geography["category_bindings"],
                                       report["counts"], FILL_COLORS)

            by_id = {entity["id"]: entity for entity in geography["entities"]}
            by_id[20]["color_rgb"] = by_id[30]["color_rgb"] = None
            for neighbor_id in (20, 30):
                with self.subTest(neighbor_id=neighbor_id):
                    by_id[neighbor_id]["color_rgb"] = by_id[10]["color_rgb"]
                    with self.assertRaisesRegex(
                        ValueError, f"neighboring land entities 10 and {neighbor_id}"
                    ):
                        build_modes()
                    by_id[neighbor_id]["color_rgb"] = None
            colors = {entry["id"]: entry["color"] for entry in build_modes()[0]["legend"]}
            self.assertNotEqual(colors[10], colors[20])
            self.assertNotEqual(colors[10], colors[30])

    def test_overview_pairs_cross_water_and_wrap_only_horizontally(self):
        overview = np.array([
            [10, 0, 0, 0, 0, 0, 20, 0],
            [0,  0, 0, 30, 0, 0, 0,  0],
            [0,  0, 0, 0, 0, 0, 0,  0],
            [0,  0, 0, 40, 0, 0, 0,  0],
            [0,  0, 0, 0, 0, 0, 0,  0],
            [50, 0, 0, 0, 0, 0, 0,  0],
        ], dtype=np.uint32)
        self.assertEqual(nearby_land_pairs(overview, radius=2), {
            (10 << 32) | 20, (30 << 32) | 40,
        })

    def test_nested_modes_count_every_cell_once_and_merge_dissolved_borders(self):
        grid = Grid(8, 4, 45)
        geography = selection()["geography"]
        geography["levels"] += [
            dict(id="area", parent_id="region"),
            dict(id="region", parent_id="continent"),
            dict(id="continent", parent_id="world"),
            dict(id="province", parent_id="area"),
        ]
        for entity_id, level_id, parent_id, name, color, kind in [
            (1, "continent", 0, "West", "#C96F62", "mixed"),
            (2, "continent", 0, "East", "#D6A34A", "mixed"),
            (4, "region", 1, "West region", "#559987", "mixed"),
            (8, "region", 2, "East region", None, "land"),
            (9, "area", 4, "Western coast", None, "land"),
            (10, "province", 9, "Unbuilt province", None, "land"),
        ]:
            geography["entities"].append(dict(
                id=entity_id, level_id=level_id, parent_id=parent_id, name=name,
                color_rgb=color, physical_class=kind,
            ))
        bindings = [
            dict(code=code, entity_id=entity_id, physical_class=kind)
            for code, entity_id, kind in [
                (1, 2, "water"), (2, 4, "water"), (3, 4, "land"),
                (4, 8, "land"), (5, 9, "land"), (6, 10, "land"),
            ]
        ]
        with TemporaryDirectory() as folder:
            directory = Path(folder)
            report = write_layer(directory / "grid", grid, [
                (y, [(0, 1, 1), (1, 2, 2), (2, 3, 3), (3, 6, 5), (6, 8, 4)])
                for y in range(4)
            ])
            modes = build_map_modes(directory / "grid", grid, geography, bindings, report["counts"], FILL_COLORS)
            self.assertEqual([mode["level_id"] for mode in modes], ["continent", "region", "area"])
            expected = [
                ([2, 1, 1, 2, 1, None], {1: 20, 2: 12}, 0),
                ([None, 4, 4, 8, 4, None], {4: 20, 8: 8}, 4),
                ([None, None, None, None, 9, None], {9: 12}, 20),
            ]
            for saved, (mapping, totals, unbuilt) in zip(modes, expected, strict=True):
                self.assertEqual(saved["entity_ids_by_category"], mapping)
                self.assertEqual({e["id"]: e["count"] for e in saved["legend"]}, totals)
                self.assertEqual(saved["unbuilt_cells"], unbuilt)
                self.assertEqual(sum(totals.values()) + unbuilt, grid.width * grid.height)
