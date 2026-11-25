"""Choose reproducible land colors that distinguish neighboring entities."""

import heapq
from collections.abc import Iterable
from functools import cache

import numpy as np
from scipy.spatial import cKDTree  # pyright: ignore[reportAttributeAccessIssue]

type RGB = tuple[int, int, int]

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
        np.linspace(0.045, 0.10, 5),
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


def choose_muted_land_color(
    neighbor_colors: set[RGB],
    fill_colors: tuple[RGB, RGB],
) -> RGB:
    """Choose the muted color most distinct from nearby land and the fixed fills.

    Args:
        neighbor_colors: Colors of already colored land with a shared edge or
            close on the overview map.
        fill_colors: Fixed RGB colors in (water, unassigned land) order.

    Returns:
        8-bit sRGB triple. Among eligible choices, maximize the OKLab distance
        to the nearest comparison color. Exact ties use RGB order.

    Raises:
        ValueError: Every sample is already used by nearby land or as a fill.
    """
    colors, lab = muted_color_samples()
    excluded = neighbor_colors.union(fill_colors)
    available = np.fromiter(
        (color not in excluded for color in colors), dtype=bool, count=len(colors)
    )
    if not available.any():
        raise ValueError("ran out of distinct muted land colors")
    comparisons = oklab(sorted(excluded))
    nearest, _ = cKDTree(comparisons).query(lab)
    nearest[~available] = -np.inf
    return colors[int(nearest.argmax())]


def color_land(
    neighbors: dict[int, set[int]],
    authored: dict[int, RGB],
    fill_colors: tuple[RGB, RGB],
) -> dict[int, RGB]:
    """Choose land colors in order of how constrained each entity is.

    Args:
        neighbors: Each land entity and its neighbors. Include land sharing an
            edge or close on the overview, and isolated land with an empty set.
        authored: Fixed colors keyed by land entity ID.
        fill_colors: Fixed RGB colors in (water, unassigned land) order.

    Returns:
        Land entity ID to 8-bit sRGB triple.

    Raises:
        ValueError: Neighboring authored colors conflict or no color is available.
    """
    colors = authored.copy()
    for entity, color in authored.items():
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
    queue = [
        (-len(seen), -len(neighbors[entity]), entity) for entity, seen in used.items()
    ]
    heapq.heapify(queue)
    while queue:
        saturation, _, entity = heapq.heappop(queue)
        if entity in colors or -saturation != len(used[entity]):
            continue
        color = choose_muted_land_color(used[entity], fill_colors)
        colors[entity] = color
        for neighbor in neighbors[entity]:
            if neighbor not in colors and color not in used[neighbor]:
                used[neighbor].add(color)
                heapq.heappush(
                    queue, (-len(used[neighbor]), -len(neighbors[neighbor]), neighbor)
                )
    return colors
