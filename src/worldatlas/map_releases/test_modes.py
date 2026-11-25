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
from worldatlas.map_releases.modes import build_map_modes, land_code_relationships, nearby_land_pairs


FILL_COLORS = (60, 98, 120), (227, 222, 210)


class PaletteTests(TestCase):
    def test_choice_maximizes_the_separation_from_its_closest_color(self):
        neighbor = (201, 111, 98)
        chosen = choose_muted_land_color({neighbor}, {neighbor}, FILL_COLORS)
        candidates, lab = muted_color_samples()
        possible = [i for i, color in enumerate(candidates) if color not in (neighbor, *FILL_COLORS)]
        references = oklab([neighbor, *FILL_COLORS])
        distances = np.linalg.norm(lab[:, None] - references, axis=2).min(axis=1)
        self.assertEqual(chosen, candidates[max(possible, key=lambda i: distances[i])])

    def test_coloring_preserves_authored_colors_and_rejects_conflicting_borders(self):
        fixed = (201, 111, 98)
        graph = {1: {2}, 2: {1}, 3: set()}
        nearby = {entity: set() for entity in graph}
        colors = color_land(graph, nearby, {1: fixed}, FILL_COLORS)
        self.assertEqual(colors[1], fixed)
        self.assertNotEqual(colors[2], fixed)
        self.assertEqual(colors[3], choose_muted_land_color(set(), set(), FILL_COLORS))
        with self.assertRaisesRegex(ValueError, "entities 1 and 2 share"):
            color_land(graph, nearby, {1: fixed, 2: fixed}, FILL_COLORS)

    def test_across_water_prefers_visibly_different_colors(self):
        fixed = choose_muted_land_color(set(), set(), FILL_COLORS)
        borders = {1: set(), 2: set()}
        nearby = {1: {2}, 2: {1}}
        colors = color_land(borders, nearby, {1: fixed}, FILL_COLORS)
        self.assertNotEqual(colors[2], fixed)
        self.assertEqual(
            color_land(borders, nearby, {1: fixed, 2: fixed}, FILL_COLORS),
            {1: fixed, 2: fixed},
        )

    def test_many_adjacent_entities_use_distinct_generated_colors(self):
        ids = set(range(10))
        graph = {entity: ids - {entity} for entity in ids}
        nearby = {entity: set() for entity in graph}
        colors = color_land(graph, nearby, {}, FILL_COLORS)
        self.assertEqual(len(set(colors.values())), len(graph))
        self.assertFalse(set(colors.values()).intersection(FILL_COLORS))
        reverse = dict(reversed(list(graph.items())))
        self.assertEqual(color_land(reverse, nearby, {}, FILL_COLORS), colors)

    def test_an_exhausted_palette_reports_the_conflict(self):
        color = (201, 111, 98)
        with patch("worldatlas.map_releases.colors.muted_color_samples",
                   return_value=((color,), oklab([color]))):
            with self.assertRaisesRegex(ValueError, "ran out of distinct muted land colors"):
                choose_muted_land_color({color}, {color}, FILL_COLORS)


class ModeTests(TestCase):
    def test_only_land_edges_contribute_including_at_the_dateline(self):
        grid = Grid(8, 4, 45)
        with TemporaryDirectory() as folder:
            path = Path(folder) / "grid"
            write_layer(path, grid, [
                (0, [(0, 1, 10), (1, 2, 20), (2, 7, 9), (7, 8, 0xFFFFFFFF)]),
                (1, [(0, 1, 30), (1, 8, 9)]),
            ])
            self.assertEqual(land_code_relationships(path, grid, []), (set(), set()))
            self.assertEqual(land_code_relationships(path, grid, [10, 20, 30, 0xFFFFFFFF]), (
                {(10, 20), (10, 30), (10, 0xFFFFFFFF)}, set(),
            ))

    def test_native_scan_detects_a_water_gap_in_the_overview(self):
        grid = Grid(1440, 9, 0.25)
        with TemporaryDirectory() as folder:
            path = Path(folder) / "grid"
            write_layer(path, grid, [
                (3, [(0, 2, 10), (2, 4, 9), (4, 6, 20)]),
                (8, [(0, 2, 10), (2, 4, 30)]),
            ])
            self.assertEqual(
                land_code_relationships(path, grid, [10, 20, 30]),
                ({(10, 30)}, {(10, 20)}),
            )

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
