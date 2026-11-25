"""Choose reproducible land colors that distinguish neighboring entities."""

import heapq
from collections import Counter
from collections.abc import Iterable
from functools import cache

import numpy as np

type RGB = tuple[int, int, int]

MUTED_ATLAS: tuple[RGB, ...] = (
    (201, 111, 98),
    (214, 163, 74),
    (135, 150, 85),
    (85, 153, 135),
    (137, 121, 172),
    (185, 119, 146),
)
# Fill colors belong to the same scheme. Use a darker slate blue for water
# and a light warm gray for land with no owner at this level.
WATER: RGB = (60, 98, 120)
UNBUILT_LAND: RGB = (227, 222, 210)
_RESERVED_FILLS = frozenset((WATER, UNBUILT_LAND))

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
def extra_muted_shades() -> tuple[RGB, ...]:
    """Sample the same muted range at more lightnesses and hues.

    Returns:
        Sorted unique 8-bit sRGB triples. Colors outside sRGB are discarded
        before rounding, so clipping cannot shift their hue.
    """
    lightness, chroma, hue = np.meshgrid(
        [0.56, 0.64, 0.72, 0.80], [0.07, 0.11, 0.15], np.deg2rad(np.arange(0, 360, 5))
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
    return tuple(
        sorted(
            {
                (int(red), int(green), int(blue))
                for red, green, blue in np.rint(rgb * 255)
            }
            - {UNBUILT_LAND}
        )
    )


def color_land(
    neighbors: dict[int, set[int]],
    nearby: dict[int, set[int]],
    authored: dict[int, RGB],
) -> dict[int, RGB]:
    """Choose land colors in order of how constrained each entity is.

    Args:
        neighbors: Land entity ID to IDs sharing a land edge. Include isolated
            entities with an empty set.
        nearby: Land IDs that look close on the overview, including across water.
        authored: Fixed colors keyed by land entity ID.

    Returns:
        Land entity ID to 8-bit sRGB triple.

    Raises:
        ValueError: Adjacent authored colors conflict or no swatch is available.
    """
    colors = authored.copy()
    usage = Counter(colors.values())
    for entity, color in authored.items():
        for neighbor in neighbors[entity]:
            if neighbor > entity and authored.get(neighbor) == color:
                raise ValueError(
                    f"adjacent land entities {entity} and {neighbor} share {color}"
                )

    visible = {
        entity: adjacent | nearby[entity] for entity, adjacent in neighbors.items()
    }
    used = {
        entity: {authored[neighbor] for neighbor in adjacent if neighbor in authored}
        for entity, adjacent in visible.items()
        if entity not in authored
    }
    queue = [
        (-len(seen), -len(visible[entity]), entity) for entity, seen in used.items()
    ]
    heapq.heapify(queue)
    while queue:
        saturation, _, entity = heapq.heappop(queue)
        if entity in colors or -saturation != len(used[entity]):
            continue
        # Close land across water affects the contrast score. Only a true
        # border makes a duplicate color a hard conflict.
        excluded = _RESERVED_FILLS | {
            colors[neighbor] for neighbor in neighbors[entity] if neighbor in colors
        }
        candidates = [color for color in MUTED_ATLAS if color not in excluded]
        if not candidates:
            candidates = [
                color for color in extra_muted_shades() if color not in excluded
            ]
        if not candidates:
            raise ValueError(f"ran out of distinct land colors at entity {entity}")
        if used[entity]:
            # The closest neighbor determines how easy a choice is to distinguish.
            delta = (
                oklab(candidates)[:, None, :] - oklab(sorted(used[entity]))[None, :, :]
            )
            distance_sq = np.sum(delta * delta, axis=2)
            color = candidates[int(distance_sq.min(axis=1).argmax())]
        else:
            # With no colored neighbors, introduce unused swatches first.
            color = min(candidates, key=usage.__getitem__)
        colors[entity] = color
        usage[color] += 1
        for neighbor in visible[entity]:
            if neighbor not in colors and color not in used[neighbor]:
                used[neighbor].add(color)
                heapq.heappush(
                    queue, (-len(used[neighbor]), -len(visible[neighbor]), neighbor)
                )
    return colors
