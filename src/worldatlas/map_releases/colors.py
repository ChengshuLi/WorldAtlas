"""Choose reproducible land colors that distinguish neighboring entities."""

import heapq
from collections.abc import Iterable
from functools import cache

import numpy as np
from scipy.spatial import cKDTree  # pyright: ignore[reportAttributeAccessIssue]

type RGB = tuple[int, int, int]

_MIN_NEARBY_CONTRAST_FRACTION = 0.85

# CSS Color 4 converts linear RGB to LMS, takes the cube root of each
# channel, then converts those values to OKLab.
_LINEAR_RGB_TO_LMS = np.array(
    [
        [0.4122214708, 0.5363325363, 0.0514459929],
        [0.2119034982, 0.6806995451, 0.1073969566],
        [0.0883024619, 0.2817188376, 0.6299787005],
    ]
)
_CUBE_ROOT_LMS_TO_OKLAB = np.array(
    [
        [0.2104542553, 0.7936177850, -0.0040720468],
        [1.9779984951, -2.4285922050, 0.4505937099],
        [0.0259040371, 0.7827717662, -0.8086757660],
    ]
)


def rgb_to_oklab(colors: Iterable[RGB]) -> np.ndarray:
    """Convert sRGB colors to OKLab so distances approximate visual differences.

    Args:
        colors: sRGB triples with integer channels from 0 to 255.

    Returns:
        Float array of shape (number of colors, 3), in L, a, b order.
    """
    normalized_rgb = np.array(list(colors), dtype=np.float64) / 255
    linear_rgb = np.where(
        normalized_rgb <= 0.04045,
        normalized_rgb / 12.92,
        ((normalized_rgb + 0.055) / 1.055) ** 2.4,
    )
    return np.cbrt(linear_rgb @ _LINEAR_RGB_TO_LMS.T) @ _CUBE_ROOT_LMS_TO_OKLAB.T


@cache
def sample_muted_land_colors() -> tuple[tuple[RGB, ...], np.ndarray]:
    """Generate and cache muted land colors at regular intervals in OKLCH.

    Returns:
        A pair containing sorted, unique 8-bit sRGB triples and a float array
        with one (L, a, b) row per triple, in the same order.
    """
    lightness, chroma, hue = np.meshgrid(
        np.linspace(0.56, 0.80, 7),
        np.linspace(0.10, 0.14, 5),
        np.deg2rad(np.arange(0, 360, 5)),
    )
    sampled_oklab = np.column_stack(
        (
            lightness.ravel(),
            (chroma * np.cos(hue)).ravel(),
            (chroma * np.sin(hue)).ravel(),
        )
    )
    cube_root_lms = sampled_oklab @ np.linalg.inv(_CUBE_ROOT_LMS_TO_OKLAB).T
    linear_rgb = cube_root_lms**3 @ np.linalg.inv(_LINEAR_RGB_TO_LMS).T
    # Drop samples that sRGB cannot display. Clipping a channel can shift the hue.
    linear_rgb = linear_rgb[np.all((0 <= linear_rgb) & (linear_rgb <= 1), axis=1)]
    normalized_rgb = np.where(
        linear_rgb <= 0.0031308,
        12.92 * linear_rgb,
        1.055 * linear_rgb ** (1 / 2.4) - 0.055,
    )
    colors = tuple(
        sorted(
            {
                (int(red), int(green), int(blue))
                for red, green, blue in np.rint(normalized_rgb * 255)
            }
        )
    )
    # Compare the actual rounded colors that the viewer will display.
    return colors, rgb_to_oklab(colors)


class LandColorPicker:
    """Choose colors for one map view and track the land colors it uses."""

    def __init__(
        self, reserved_colors: set[RGB], authored_colors: Iterable[RGB]
    ) -> None:
        """Prepare the candidate colors and account for saved land colors.

        Args:
            reserved_colors: Exact RGBs for water and unassigned land.
            authored_colors: Land colors saved in Neon for this view's level.
        """
        self._candidate_colors, self._candidate_oklab_coordinates = (
            sample_muted_land_colors()
        )
        self._candidate_index_by_rgb = {
            color: index for index, color in enumerate(self._candidate_colors)
        }
        self._unreserved_candidates = np.array(
            [color not in reserved_colors for color in self._candidate_colors],
            dtype=bool,
        )
        self._used_land_colors = set(authored_colors)
        self._closest_view_distance = np.full(len(self._candidate_colors), np.inf)
        if self._used_land_colors:
            used_colors = cKDTree(rgb_to_oklab(sorted(self._used_land_colors)))
            self._closest_view_distance, _ = used_colors.query(
                self._candidate_oklab_coordinates
            )

    def choose_muted_land_color(self, neighbor_colors: set[RGB]) -> RGB:
        """Pick a land color and record it for future choices in this view.

        Args:
            neighbor_colors: Colors of nearby assigned land and any nearby water.

        Returns:
            An 8-bit sRGB triple. For each candidate, nearby contrast is its
            OKLab distance to the closest nearby color. Keep candidates with
            at least 85% of the best nearby contrast. Among those, maximize the
            distance to the closest land color used anywhere in this view.
            Break ties by nearby contrast, then by ascending RGB order.

        Raises:
            ValueError: Every candidate color is already used nearby or reserved.
        """
        eligible_candidates = self._unreserved_candidates.copy()
        for color in neighbor_colors:
            if (index := self._candidate_index_by_rgb.get(color)) is not None:
                eligible_candidates[index] = False
        if not eligible_candidates.any():
            raise ValueError("ran out of distinct muted land colors")

        if neighbor_colors:
            nearby_distances, _ = cKDTree(rgb_to_oklab(sorted(neighbor_colors))).query(
                self._candidate_oklab_coordinates
            )
            best_nearby_distance = nearby_distances[eligible_candidates].max()
            eligible_candidates &= (
                nearby_distances >= _MIN_NEARBY_CONTRAST_FRACTION * best_nearby_distance
            )
        else:
            # With no nearby comparison, every eligible color has the same score.
            nearby_distances = np.full(len(self._candidate_colors), np.inf)

        best_view_distance = self._closest_view_distance[eligible_candidates].max()
        view_distance_finalists = eligible_candidates & (
            self._closest_view_distance == best_view_distance
        )
        # Among finalists, take the strongest nearby contrast. Keep the full array
        # so argmax returns the original index and picks the first RGB on a tie.
        winning_index = int(
            np.where(view_distance_finalists, nearby_distances, -np.inf).argmax()
        )
        chosen_color = self._candidate_colors[winning_index]
        if chosen_color not in self._used_land_colors:
            self._used_land_colors.add(chosen_color)
            # Update each candidate's closest distance using the one new color.
            distance_to_new_color = np.linalg.norm(
                self._candidate_oklab_coordinates
                - self._candidate_oklab_coordinates[winning_index],
                axis=1,
            )
            np.minimum(
                self._closest_view_distance,
                distance_to_new_color,
                out=self._closest_view_distance,
            )
        return chosen_color


def assign_land_colors(
    land_neighbors_by_entity: dict[int, set[int]],
    land_near_water: set[int],
    authored_colors: dict[int, RGB],
    fill_colors: tuple[RGB, RGB],
) -> dict[int, RGB]:
    """Preserve saved land colors and choose colors for the other entities.

    Args:
        land_neighbors_by_entity: Every entity with land cells at this level,
            mapped to the IDs of other land entities that share a cell edge or
            appear close on the overview map (within about two degrees at the
            usual world resolution, as measured by ``scan_color_neighbors``).
            For example, {10: {20}, 20: {10}, 30: set()} means 10 and 20 are
            neighbors, and 30 has no land neighbors.
        land_near_water: IDs of land entities that share a cell edge with water
            or are within the overview map's proximity radius of water.
        authored_colors: Land entity IDs mapped to saved Neon color overrides,
            expressed as 8-bit sRGB triples. For example, {10: (185, 90, 70)}
            keeps that color for entity 10. Every other entity gets a generated
            color.
        fill_colors: Two 8-bit sRGB triples in (water, unassigned land) order.

    Returns:
        A dictionary mapping each land entity ID to its 8-bit sRGB triple.

    Raises:
        ValueError: An authored color is reserved, neighboring authored colors
            conflict, or no generated color is available.
    """
    water_color, unassigned_land_color = fill_colors
    reserved_colors = {water_color, unassigned_land_color}
    land_colors = authored_colors.copy()
    for entity_id, color in authored_colors.items():
        if color in reserved_colors:
            raise ValueError(f"land entity {entity_id} uses reserved color {color}")
        for neighbor_id in land_neighbors_by_entity[entity_id]:
            if neighbor_id > entity_id and authored_colors.get(neighbor_id) == color:
                raise ValueError(
                    f"neighboring land entities {entity_id} and {neighbor_id} "
                    f"share {color}"
                )

    nearby_colors_by_entity = {
        entity_id: {
            authored_colors[neighbor_id]
            for neighbor_id in neighbor_ids
            if neighbor_id in authored_colors
        }
        for entity_id, neighbor_ids in land_neighbors_by_entity.items()
        if entity_id not in authored_colors
    }
    for entity_id in land_near_water.intersection(nearby_colors_by_entity):
        nearby_colors_by_entity[entity_id].add(water_color)
    # The heap takes the smallest tuple first. Negative counts put entities
    # with more distinct nearby colors first, then those with more land
    # neighbors. Entity ID breaks any remaining tie.
    color_queue = [
        (-len(nearby_colors), -len(land_neighbors_by_entity[entity_id]), entity_id)
        for entity_id, nearby_colors in nearby_colors_by_entity.items()
    ]
    heapq.heapify(color_queue)
    picker = LandColorPicker(reserved_colors, land_colors.values())
    while color_queue:
        _, _, entity_id = heapq.heappop(color_queue)
        # An updated priority comes out first. Skip the older entry once colored.
        if entity_id in land_colors:
            continue
        color = picker.choose_muted_land_color(nearby_colors_by_entity[entity_id])
        land_colors[entity_id] = color
        for neighbor_id in land_neighbors_by_entity[entity_id]:
            if (
                neighbor_id not in land_colors
                and color not in nearby_colors_by_entity[neighbor_id]
            ):
                nearby_colors_by_entity[neighbor_id].add(color)
                heapq.heappush(
                    color_queue,
                    (
                        -len(nearby_colors_by_entity[neighbor_id]),
                        -len(land_neighbors_by_entity[neighbor_id]),
                        neighbor_id,
                    ),
                )
    return land_colors
