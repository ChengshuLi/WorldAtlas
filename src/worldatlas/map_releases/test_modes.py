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
    LandColorPicker,
    assign_land_colors,
    rgb_to_oklab,
    sample_muted_land_colors,
)
from worldatlas.map_releases.modes import (
    build_map_modes,
    overview_neighbor_pairs,
    scan_color_neighbors,
)

FILL_COLORS = (60, 98, 120), (227, 222, 210)
RESERVED = set(FILL_COLORS)


class PaletteTests(TestCase):
    def test_choice_maximizes_the_separation_from_its_closest_color(self):
        neighbor = (201, 111, 98)
        picked = LandColorPicker(RESERVED, ())
        chosen = picked.choose_muted_land_color({neighbor})
        candidates, lab = sample_muted_land_colors()
        possible = [i for i, color in enumerate(candidates) if color not in (neighbor, *FILL_COLORS)]
        references = rgb_to_oklab([neighbor])
        distances = np.linalg.norm(lab[:, None] - references, axis=2).min(axis=1)
        self.assertEqual(chosen, candidates[max(possible, key=lambda i: distances[i])])

    def test_view_variety_keeps_at_least_85_percent_of_nearby_contrast(self):
        water = FILL_COLORS[0]
        original = LandColorPicker(RESERVED, ()).choose_muted_land_color({water})
        picked = LandColorPicker(RESERVED, (original,))
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
        with patch("worldatlas.map_releases.colors.sample_muted_land_colors",
                   return_value=(swatches, rgb_to_oklab(swatches))):
            picked = LandColorPicker({swatches[0]}, ())
            first, second, third = (picked.choose_muted_land_color(set()) for _ in range(3))
        self.assertEqual((first, second, third), (swatches[1], swatches[2], swatches[1]))

    def test_coloring_preserves_authored_colors_and_rejects_conflicting_borders(self):
        fixed = (201, 111, 98)
        graph = {1: {2}, 2: {1}, 3: set()}
        colors = assign_land_colors(graph, set(), {1: fixed}, FILL_COLORS)
        self.assertEqual(colors[1], fixed)
        self.assertNotEqual(colors[2], fixed)
        self.assertEqual(len(set(colors.values())), 3)
        with self.assertRaisesRegex(ValueError, "entities 1 and 2 share"):
            assign_land_colors(graph, set(), {1: fixed, 2: fixed}, FILL_COLORS)

    def test_authored_colors_cannot_use_the_two_reserved_values(self):
        for fill in FILL_COLORS:
            with self.subTest(fill=fill):
                with self.assertRaisesRegex(ValueError, "land entity 1 uses reserved"):
                    assign_land_colors({1: set()}, set(), {1: fill}, FILL_COLORS)

    def test_palette_has_richer_saturation_and_the_fills_are_outside_it(self):
        samples, lab = sample_muted_land_colors()
        chroma = np.linalg.norm(lab[:, 1:], axis=1)
        # Round to the intended precision to account for storing 8-bit RGB.
        self.assertTrue(np.all((0.10 <= np.round(chroma, 2)) & (np.round(chroma, 2) <= 0.14)))
        self.assertTrue(set(samples).isdisjoint(FILL_COLORS))

    def test_many_adjacent_entities_use_distinct_generated_colors(self):
        ids = set(range(10))
        graph = {entity: ids - {entity} for entity in ids}
        colors = assign_land_colors(graph, set(), {}, FILL_COLORS)
        self.assertEqual(len(set(colors.values())), len(graph))
        self.assertFalse(set(colors.values()).intersection(FILL_COLORS))
        reverse = dict(reversed(list(graph.items())))
        self.assertEqual(assign_land_colors(reverse, set(), {}, FILL_COLORS), colors)

    def test_an_exhausted_palette_reports_the_conflict(self):
        color = (201, 111, 98)
        with patch("worldatlas.map_releases.colors.sample_muted_land_colors",
                   return_value=((color,), rgb_to_oklab([color]))):
            with self.assertRaisesRegex(ValueError, "ran out of distinct muted land colors"):
                LandColorPicker(RESERVED, ()).choose_muted_land_color({color})


class ModeTests(TestCase):
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
                scan_color_neighbors(path, grid, (10, 20, 30, 0xFFFFFFFF)),
                ({(10, 20), (10, 30), (10, 0xFFFFFFFF)}, {20, 30, 0xFFFFFFFF}),
            )

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
            pairs, _ = scan_color_neighbors(path, grid, codes)
            self.assertEqual(pairs, {(10, 30), (10, 20)})

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
        self.assertEqual(overview_neighbor_pairs(overview, radius=2), {
            (10 << 32) | 20, (30 << 32) | 40, 10, 20, 30, 40, 50,
        })

    def test_modes_score_local_water_and_skip_unassigned_land(self):
        grid = Grid(24, 12, 15)
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
                color_rgb=None, physical_class=kind,
            ))
        bindings = [
            dict(code=10, entity_id=1, physical_class="land"),
            dict(code=20, entity_id=2, physical_class="land"),
            dict(code=30, entity_id=3, physical_class="land"),
            dict(code=40, entity_id=2, physical_class="water"),
        ]
        water, gray = FILL_COLORS
        land_row = [(0, 4, 10), (4, 8, 30), (8, 12, 10),
                    (12, 16, 20), (16, 20, 40), (20, 24, 10)]
        with TemporaryDirectory() as folder:
            path = Path(folder) / "grid"
            report = write_layer(path, grid, [(y, land_row) for y in range(grid.height)])
            for owner in (2, 1):
                with self.subTest(water_owner=owner):
                    bindings[-1]["entity_id"] = owner
                    modes = build_map_modes(path, grid, geography, bindings, report["counts"], FILL_COLORS)
                    colors = {row["id"]: tuple(row["color"]) for row in modes[1]["legend"]}
                    # Land entity 2 sees water, including when it owns the water.
                    picked = LandColorPicker({water, gray}, ())
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
