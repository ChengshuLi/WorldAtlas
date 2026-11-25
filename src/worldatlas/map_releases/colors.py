"""Choose reproducible land colors that distinguish neighboring entities."""

import heapq
from collections.abc import Iterable
from functools import cache

import numpy as np
from scipy.spatial import cKDTree  # pyright: ignore[reportAttributeAccessIssue]

type RGB = tuple[int, int, int]

_MIN_NEARBY_CONTRAST_FRACTION = 0.85

# The OKLab matrices convert linear sRGB via cone responses. See CSS Color 4.
_RGB_TO_LMS = np.array(
    [
        [0.4122214708, 0.5363325363, 0.0514459929],
        [0.2119034982, 0.6806995451, 0.1073969566],
        [0.0883024619, 0.2817188376, 0.6299787005],
    ]
)
_LMS_TO_LAB = np.array(
    [
        [0.2104542553, 0.7936177850, -0.0040720468],
        [1.9779984951, -2.4285922050, 0.4505937099],
        [0.0259040371, 0.7827717662, -0.8086757660],
    ]
)


def oklab(colors: Iterable[RGB]) -> np.ndarray:
    """Convert display colors to three perceptual coordinates per color.

    Args:
        colors: sRGB triples with integer channels from 0 to 255.

    Returns:
        Float array of shape (number of colors, 3), in L, a, b order.
    """
    rgb = np.array(list(colors), dtype=np.float64) / 255
    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    return np.cbrt(linear @ _RGB_TO_LMS.T) @ _LMS_TO_LAB.T


@cache
def muted_color_samples() -> tuple[tuple[RGB, ...], np.ndarray]:
    """Sample muted colors from continuous ranges of lightness, chroma, and hue.

    Returns:
        (Sorted unique 8-bit sRGB triples, matching OKLab coordinates).
        Colors outside sRGB are discarded before rounding to protect their hue.
    """
    lightness, chroma, hue = np.meshgrid(
        np.linspace(0.56, 0.80, 7),
        np.linspace(0.10, 0.14, 5),
        np.deg2rad(np.arange(0, 360, 5)),
    )
    lab = np.column_stack(
        (
            lightness.ravel(),
            (chroma * np.cos(hue)).ravel(),
            (chroma * np.sin(hue)).ravel(),
        )
    )
    linear = (lab @ np.linalg.inv(_LMS_TO_LAB).T) ** 3 @ np.linalg.inv(_RGB_TO_LMS).T
    linear = linear[np.all((0 <= linear) & (linear <= 1), axis=1)]
    rgb = np.where(
        linear <= 0.0031308, 12.92 * linear, 1.055 * linear ** (1 / 2.4) - 0.055
    )
    colors = tuple(
        sorted(
            {
                (int(red), int(green), int(blue))
                for red, green, blue in np.rint(rgb * 255)
            }
        )
    )
    return colors, oklab(colors)


class LandColorPicker:
    """Keep each candidate’s distance from the closest land color in this view."""

    def __init__(
        self, reserved_colors: set[RGB], authored_colors: Iterable[RGB]
    ) -> None:
        """Prepare the candidate colors and account for saved land colors.

        Args:
            reserved_colors: Exact RGBs for water and unassigned land.
            authored_colors: Colors already assigned to land by the input catalog.
        """
        self._colors, self._candidate_oklab_coordinates = muted_color_samples()
        self._index_by_color = {color: i for i, color in enumerate(self._colors)}
        self._available = np.array(
            [color not in reserved_colors for color in self._colors], dtype=bool
        )
        self._used = set(authored_colors)
        self._closest_view_distance = np.full(len(self._colors), np.inf)
        if self._used:
            self._closest_view_distance, _ = cKDTree(oklab(sorted(self._used))).query(
                self._candidate_oklab_coordinates
            )

    def choose_muted_land_color(self, neighbor_colors: set[RGB]) -> RGB:
        """Pick a land color and record it for future choices in this view.

        Args:
            neighbor_colors: Colors of nearby assigned land and any nearby water.

        Returns:
            An 8-bit RGB triple. Keep candidates with at least 85% of the best
            nearby contrast. Among those, maximize the distance to the closest
            land color used anywhere in the view. Break ties by nearby contrast
            and then RGB order.

        Raises:
            ValueError: Every candidate color is already used nearby or reserved.
        """
        available = self._available.copy()
        for color in neighbor_colors:
            if (index := self._index_by_color.get(color)) is not None:
                available[index] = False
        if not available.any():
            raise ValueError("ran out of distinct muted land colors")

        if neighbor_colors:
            nearby, _ = cKDTree(oklab(sorted(neighbor_colors))).query(
                self._candidate_oklab_coordinates
            )
            best_nearby = nearby[available].max()
            available &= nearby >= _MIN_NEARBY_CONTRAST_FRACTION * best_nearby
        else:
            # With no nearby comparison, every eligible color has the same score.
            nearby = np.full(len(self._colors), np.inf)

        best_view = self._closest_view_distance[available].max()
        available &= self._closest_view_distance == best_view
        winner = int(np.where(available, nearby, -np.inf).argmax())
        color = self._colors[winner]
        if color not in self._used:
            self._used.add(color)
            # A new color can only decrease each candidate’s closest distance.
            distance_to_color = np.linalg.norm(
                self._candidate_oklab_coordinates
                - self._candidate_oklab_coordinates[winner],
                axis=1,
            )
            np.minimum(
                self._closest_view_distance,
                distance_to_color,
                out=self._closest_view_distance,
            )
        return color


def color_land(
    neighbors: dict[int, set[int]],
    land_near_water: set[int],
    authored: dict[int, RGB],
    fill_colors: tuple[RGB, RGB],
) -> dict[int, RGB]:
    """Choose land colors in order of how constrained each entity is.

    Args:
        neighbors: Each land entity and its neighbors. Include land sharing an
            edge or close on the overview, and isolated land with an empty set.
        land_near_water: IDs of land entities with water visible nearby.
        authored: Fixed colors keyed by land entity ID.
        fill_colors: Fixed RGB colors in (water, unassigned land) order.

    Returns:
        Land entity ID to 8-bit sRGB triple.

    Raises:
        ValueError: An authored color is reserved, neighboring authored colors
            conflict, or no generated color is available.
    """
    water, unassigned = fill_colors
    reserved = {water, unassigned}
    colors = authored.copy()
    for entity, color in authored.items():
        if color in reserved:
            raise ValueError(f"land entity {entity} uses reserved color {color}")
        for neighbor in neighbors[entity]:
            if neighbor > entity and authored.get(neighbor) == color:
                raise ValueError(
                    f"neighboring land entities {entity} and {neighbor} share {color}"
                )

    used = {
        entity: {authored[neighbor] for neighbor in adjacent if neighbor in authored}
        for entity, adjacent in neighbors.items()
        if entity not in authored
    }
    for entity in land_near_water.intersection(used):
        used[entity].add(water)
    queue = [
        (-len(seen), -len(neighbors[entity]), entity) for entity, seen in used.items()
    ]
    heapq.heapify(queue)
    picker = LandColorPicker(reserved, colors.values())
    while queue:
        saturation, _, entity = heapq.heappop(queue)
        if entity in colors or -saturation != len(used[entity]):
            continue
        color = picker.choose_muted_land_color(used[entity])
        colors[entity] = color
        for neighbor in neighbors[entity]:
            if neighbor not in colors and color not in used[neighbor]:
                used[neighbor].add(color)
                heapq.heappush(
                    queue, (-len(used[neighbor]), -len(neighbors[neighbor]), neighbor)
                )
    return colors
