"""Verify edge adjacency, color choices, and the lookup for each actual level."""

from itertools import combinations
from pathlib import Path
from random import Random
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import write_layer
from worldatlas.map_build.test_support import selection
from worldatlas.map_build.display.colors import (
    LandColorPicker,
    assign_land_colors,
    rgb_to_oklab,
    sample_muted_land_colors,
)
from worldatlas.map_build.display.modes import build_map_modes, save_generated_colors
from worldatlas.map_build.display.neighbors import runs_within_distance, scan_color_neighbors

FILL_COLORS = (60, 98, 120), (227, 222, 210)
RESERVED = set(FILL_COLORS)


class PaletteTests(TestCase):
    def test_choice_maximizes_the_separation_from_its_closest_color(self):
        neighbor = (201, 111, 98)
        picked = LandColorPicker(RESERVED)
        chosen = picked.choose_muted_land_color({neighbor})
        candidates, lab = sample_muted_land_colors()
        possible = [i for i, color in enumerate(candidates) if color not in (neighbor, *FILL_COLORS)]
        references = rgb_to_oklab([neighbor])
        distances = np.linalg.norm(lab[:, None] - references, axis=2).min(axis=1)
        self.assertEqual(chosen, candidates[max(possible, key=lambda i: distances[i])])

    def test_view_variety_keeps_at_least_85_percent_of_nearby_contrast(self):
        water = FILL_COLORS[0]
        picked = LandColorPicker(RESERVED)
        original = picked.choose_muted_land_color({water})
        chosen = picked.choose_muted_land_color({water})

        candidates, lab = sample_muted_land_colors()
        local = np.linalg.norm(lab - rgb_to_oklab([water])[0], axis=1)
        view = np.linalg.norm(lab - rgb_to_oklab([original])[0], axis=1)
        eligible = [i for i, color in enumerate(candidates) if color not in RESERVED]
        best_local = max(local[i] for i in eligible)
        shortlist = [i for i in eligible if local[i] >= 0.85 * best_local]
        expected = candidates[max(shortlist, key=lambda i: (view[i], local[i]))]
        self.assertEqual(chosen, expected)
        self.assertNotEqual(chosen, original)

    def test_distant_entities_can_reuse_colors_after_the_palette_is_used(self):
        swatches = ((80, 140, 60), (210, 150, 100), (200, 100, 110))
        with patch("worldatlas.map_build.display.colors.sample_muted_land_colors",
                   return_value=(swatches, rgb_to_oklab(swatches))):
            picked = LandColorPicker({swatches[0]})
            first, second, third = (picked.choose_muted_land_color(set()) for _ in range(3))
        self.assertEqual((first, second, third), (swatches[1], swatches[2], swatches[1]))

    def test_palette_has_richer_saturation_and_the_fills_are_outside_it(self):
        samples, lab = sample_muted_land_colors()
        chroma = np.linalg.norm(lab[:, 1:], axis=1)
        # Round to the intended precision to account for storing 8-bit RGB.
        self.assertTrue(np.all((0.10 <= np.round(chroma, 2)) & (np.round(chroma, 2) <= 0.14)))
        self.assertTrue(set(samples).isdisjoint(FILL_COLORS))

    def test_many_adjacent_entities_use_distinct_generated_colors(self):
        ids = set(range(10))
        graph = {entity: ids - {entity} for entity in ids}
        colors = assign_land_colors(graph, set(), FILL_COLORS)
        self.assertEqual(len(set(colors.values())), len(graph))
        self.assertFalse(set(colors.values()).intersection(FILL_COLORS))
        reverse = dict(reversed(list(graph.items())))
        self.assertEqual(assign_land_colors(reverse, set(), FILL_COLORS), colors)

    def test_an_exhausted_palette_reports_the_conflict(self):
        color = (201, 111, 98)
        with patch("worldatlas.map_build.display.colors.sample_muted_land_colors",
                   return_value=((color,), rgb_to_oklab([color]))):
            with self.assertRaisesRegex(ValueError, "ran out of distinct muted land colors"):
                LandColorPicker(RESERVED).choose_muted_land_color({color})


class ModeTests(TestCase):
    def test_water_legend_uses_no_per_entity_rgb(self):
        grid = Grid(4, 1, 90.0)
        geography = selection()["geography"]
        geography["levels"].append(dict(id="continent", parent_id="world"))
        geography["entities"].extend([
            dict(id=1, name="Land", level_id="continent", parent_id=0, physical_class="mixed"),
            dict(id=2, name="Ocean", level_id="continent", parent_id=0, physical_class="water"),
            dict(id=3, name="Mixed with only water built", level_id="continent", parent_id=0,
                 physical_class="mixed"),
        ])
        bindings = [
            dict(code=11, entity_id=1, physical_class="land"),
            dict(code=12, entity_id=1, physical_class="water"),
            dict(code=21, entity_id=2, physical_class="water"),
            dict(code=31, entity_id=3, physical_class="water"),
        ]
        with TemporaryDirectory() as folder:
            path = Path(folder) / "grid"
            report = write_layer(path, grid, [(0, [(0, 1, 11), (1, 2, 12), (2, 3, 21), (3, 4, 31)])])
            modes = build_map_modes(path, grid, geography, bindings, report["counts"], FILL_COLORS)
        land, ocean, mixed = modes[0]["legend"]
        self.assertIsNone(ocean["color"])
        self.assertIsNone(mixed["color"])
        database = Mock()
        save_generated_colors(database, modes)
        self.assertEqual(database.execute.call_args.args[1], ([1], ["#" + bytes(land["color"]).hex().upper()]))

    def test_run_search_rejects_close_bounds_without_close_cells(self):
        first = np.array([[8, 0, 1], [10, 0, 1]])
        second = np.array([[0, 0, 1], [7, 5, 6], [12, 5, 6], [20, 0, 1]])
        self.assertFalse(runs_within_distance(first, second, 360, 3, 9))
        self.assertFalse(runs_within_distance(first, second[1:2], 360, 3, 9))
        second[2, 1:] = [2, 3]
        self.assertTrue(runs_within_distance(first, second, 360, 3, 9))

    def test_tiled_scan_matches_all_cell_pairs(self):
        rng = Random(315)
        land = (7, 21, 0xFFFFFFFF)
        for trial in range(32):
            width = rng.randrange(2, 22)
            height = rng.randrange(1, width // 2 + 1)
            degrees = rng.choice((2, 30, 45, 90, 120, 180))
            grid = Grid(width, height, 360 / width)
            dense = [[rng.choice((2, 3, *land)) for _ in range(width)] for _ in range(height)]
            rows = [(y, [(x, x + 1, code) for x, code in enumerate(codes)])
                    for y, codes in enumerate(dense)]
            with self.subTest(width=width, height=height, degrees=degrees, trial=trial):
                with TemporaryDirectory() as folder:
                    directory = Path(folder) / "grid"
                    write_layer(directory, grid, rows)
                    actual = scan_color_neighbors(directory, grid, land, distance_degrees=degrees)
                cells = [(y, x, code if code in land else 0)
                         for y, codes in enumerate(dense) for x, code in enumerate(codes)]
                expected = set()
                for (y, x, code), (yy, xx, other) in combinations(cells, 2):
                    dx = min(abs(x - xx), width - abs(x - xx))
                    if code != other and ((y - yy) ** 2 + dx ** 2) * 360**2 <= (width * degrees)**2:
                        expected.add(tuple(sorted((code, other))))
                self.assertEqual(actual, (
                    {(first, second) for first, second in expected if first},
                    {second for first, second in expected if not first},
                ))

    def test_exact_cutoff_and_diagonals(self):
        grid = Grid(360, 12, 1.0)
        with TemporaryDirectory() as folder:
            directory = Path(folder) / "grid"
            write_layer(directory, grid, [
                (1, [(0, 1, 10), (358, 359, 20)]),
                (3, [(0, 1, 30), (2, 3, 40)]),
            ])
            pairs, water = scan_color_neighbors(directory, grid, (10, 20, 30, 40))
        self.assertEqual(pairs, {(10, 20), (10, 30), (30, 40)})
        self.assertEqual(water, {10, 20, 30, 40})

    def test_shared_land_and_water_edges_include_the_dateline(self):
        grid = Grid(8, 4, 45)
        with TemporaryDirectory() as folder:
            path = Path(folder) / "grid"
            write_layer(path, grid, [
                (0, [(0, 1, 10), (1, 2, 20), (2, 7, 9), (7, 8, 0xFFFFFFFF)]),
                (1, [(0, 1, 30), (1, 8, 9)]),
                (2, [(0, 8, 9)]),
                (3, [(0, 8, 9)]),
            ])
            self.assertEqual(scan_color_neighbors(path, grid, []), (set(), set()))
            self.assertEqual(
                scan_color_neighbors(path, grid, (10, 20, 30, 0xFFFFFFFF), distance_degrees=45),
                ({(10, 20), (10, 30), (10, 0xFFFFFFFF)}, {20, 30, 0xFFFFFFFF}),
            )

    def test_neighbors_across_water_follow_the_same_color_rule_as_shared_edges(self):
        grid = Grid(1440, 20, 0.25)
        geography = selection()["geography"]
        geography["levels"].append(dict(id="continent", parent_id="world"))
        codes = (10, 20, 30)
        for entity_id in codes:
            geography["entities"].append(dict(
                id=entity_id, level_id="continent", parent_id=0, name=str(entity_id),
                physical_class="land",
            ))
            geography["category_bindings"].append(dict(
                code=entity_id, entity_id=entity_id, physical_class="land",
            ))
        with TemporaryDirectory() as folder:
            path = Path(folder) / "grid"
            report = write_layer(path, grid, [
                (2, [(4, 5, 10), (5, 6, 9), (6, 7, 20)]),
                (15, [(0, 2, 10), (2, 4, 30)]),
            ])
            pairs, _ = scan_color_neighbors(path, grid, codes)
            self.assertEqual(pairs, {(10, 30), (10, 20)})

            def build_modes():
                return build_map_modes(path, grid, geography, geography["category_bindings"],
                                       report["counts"], FILL_COLORS)

            colors = {entry["id"]: entry["color"] for entry in build_modes()[0]["legend"]}
            self.assertNotEqual(colors[10], colors[20])
            self.assertNotEqual(colors[10], colors[30])

    def test_modes_score_local_water_and_skip_unassigned_land(self):
        grid = Grid(360, 12, 1.0)
        geography = selection()["geography"]
        geography["levels"] += [
            dict(id="continent", parent_id="world"),
            dict(id="subcontinent", parent_id="continent"),
        ]
        for entity_id, parent, level, kind in (
            (1, 0, "continent", "mixed"),
            (2, 1, "subcontinent", "mixed"),
            (3, 1, "subcontinent", "land"),
        ):
            geography["entities"].append(dict(
                id=entity_id, parent_id=parent, level_id=level, name=str(entity_id),
                physical_class=kind,
            ))
        bindings = [
            dict(code=10, entity_id=1, physical_class="land"),
            dict(code=20, entity_id=2, physical_class="land"),
            dict(code=30, entity_id=3, physical_class="land"),
            dict(code=40, entity_id=2, physical_class="water"),
        ]
        water, gray = FILL_COLORS
        land_row = [(0, 4, 10), (4, 8, 30), (8, 12, 10),
                    (12, 16, 20), (16, 20, 40), (20, 360, 10)]
        with TemporaryDirectory() as folder:
            path = Path(folder) / "grid"
            report = write_layer(path, grid, [(y, land_row) for y in range(grid.height)])
            for owner in (2, 1):
                with self.subTest(water_owner=owner):
                    bindings[-1]["entity_id"] = owner
                    modes = build_map_modes(path, grid, geography, bindings, report["counts"], FILL_COLORS)
                    colors = {row["id"]: tuple(row["color"]) for row in modes[1]["legend"]}
                    # Land entity 2 sees water, including when it owns the water.
                    picked = LandColorPicker({water, gray})
                    self.assertEqual(colors[2], picked.choose_muted_land_color({water}))
                    # Entity 3 sees only land without a subcontinent assignment.
                    self.assertEqual(colors[3], picked.choose_muted_land_color(set()))
                    self.assertNotEqual(colors[2], colors[3])

    def test_nested_modes_count_every_cell_once_and_merge_dissolved_borders(self):
        grid = Grid(8, 4, 45)
        geography = selection()["geography"]
        geography["levels"] += [
            dict(id="area", parent_id="region"),
            dict(id="region", parent_id="continent"),
            dict(id="continent", parent_id="world"),
            dict(id="province", parent_id="area"),
        ]
        for entity_id, level_id, parent_id, name, kind in [
            (1, "continent", 0, "West", "mixed"),
            (2, "continent", 0, "East", "mixed"),
            (4, "region", 1, "West region", "mixed"),
            (8, "region", 2, "East region", "land"),
            (9, "area", 4, "Western coast", "land"),
            (10, "province", 9, "Unbuilt province", "land"),
        ]:
            geography["entities"].append(dict(
                id=entity_id, level_id=level_id, parent_id=parent_id, name=name,
                physical_class=kind,
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
