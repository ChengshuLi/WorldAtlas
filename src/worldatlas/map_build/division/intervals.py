"""Vectorized row overlays shared by scope preparation and ownership checks."""

from collections.abc import Mapping, Sequence

import numpy as np


class Eligibility:
    """Check which physical classes each child can own."""

    def __init__(self, children: Mapping[int, str]) -> None:
        """Index the class allowed for each child.

        Args:
            children: Child entity ID mapped to "land", "water" or "mixed".

        Raises:
            ValueError: No children are supplied or a child ID is zero.
        """
        self.ids = np.asarray(sorted(children), dtype=np.uint32)
        self.kinds = np.asarray(
            [{"mixed": 0, "water": 1, "land": 17}[children[int(e)]] for e in self.ids],
            dtype=np.uint32,
        )
        if not len(self.ids) or self.ids[0] == 0:
            raise ValueError("a division requires positive child IDs")

    def invalid(self, owners: np.ndarray, physical: np.ndarray) -> np.ndarray:
        """Find owners that cannot claim their physical class.

        Args:
            owners: Array of child entity IDs.
            physical: Matching array of land (17) and water (1) codes.

        Returns:
            Bool array marking unknown owners and class mismatches.
        """
        positions = np.searchsorted(self.ids, owners)
        safe = np.minimum(positions, len(self.ids) - 1)
        found = (positions < len(self.ids)) & (self.ids[safe] == owners)
        kind = self.kinds[safe]
        return ~found | ((kind != 0) & (kind != physical))


def overlay(
    *rows: tuple[np.ndarray, np.ndarray],
) -> tuple[np.ndarray, np.ndarray, list[np.ndarray]]:
    """Split rows wherever any input changes value.

    Args:
        rows: One or more rows as (exclusive_end_columns, values) arrays.

    Returns:
        (starts, ends, aligned_values). Each input gets a value per shared
        interval. For example, runs ending at [2, 5] and [3, 5] produce
        [0, 2), [2, 3), and [3, 5).

    Raises:
        ValueError: There are no input rows or their widths differ.
    """
    if not rows:
        raise ValueError("an overlay needs at least one row")
    if not len(rows[0][0]):
        raise ValueError("overlay rows must cover at least one column")
    width = int(rows[0][0][-1])
    if any(not len(ends) or int(ends[-1]) != width for ends, _ in rows):
        raise ValueError("overlay rows have different widths")
    cuts = np.unique(np.concatenate(([0], *(ends for ends, _ in rows))))
    starts, ends = cuts[:-1], cuts[1:]
    values = [
        codes[np.searchsorted(stops, starts, side="right")] for stops, codes in rows
    ]
    return starts, ends, values


def spans(
    starts: np.ndarray, ends: np.ndarray, values: np.ndarray
) -> list[tuple[int, int, int]]:
    """Merge adjacent intervals with the same value and skip zeros.

    Args:
        starts: First column of each interval.
        ends: Exclusive end column of each interval.
        values: Code assigned to each interval.

    Returns:
        Sparse (first_column, end_column, code) records in column order.
    """
    if not len(starts):
        return []
    changes = np.flatnonzero(np.r_[True, values[1:] != values[:-1]])
    stops = ends[np.r_[changes[1:] - 1, len(ends) - 1]]
    return [
        (int(starts[i]), int(stop), int(values[i]))
        for i, stop in zip(changes, stops)
        if values[i] != 0
    ]


def prepare(
    physical: tuple[np.ndarray, np.ndarray],
    parent: tuple[np.ndarray, np.ndarray],
    selected: tuple[np.ndarray, np.ndarray],
    snapshot: tuple[np.ndarray, np.ndarray],
    *,
    physical_class: str,
    unassigned_only: bool,
) -> list[tuple[int, int, int]]:
    """Find cells a rule may assign within one row.

    Args:
        physical: Physical row runs with land or water codes.
        parent: Row runs marking cells inside the parent.
        selected: Row runs marking the rule's geographic scope.
        snapshot: Row of owner IDs before this rule group.
        physical_class: "land", "water", or "mixed" for both.
        unassigned_only: Whether to exclude cells that already have an owner.

    Returns:
        (first_column, end_column, 1) spans where the rule may assign cells.
    """
    if (
        physical_class not in ("land", "water", "mixed")
        or type(unassigned_only) is not bool
    ):
        raise ValueError("invalid physical class or unassigned_only setting")
    starts, ends, (kind, within, chosen, owners) = overlay(
        physical, parent, selected, snapshot
    )
    eligible = (within != 0) & (chosen != 0)
    if physical_class != "mixed":
        eligible &= kind == {"land": 17, "water": 1}[physical_class]
    if unassigned_only:
        eligible &= owners == 0
    return spans(starts, ends, eligible.astype(np.uint32))


def combine(
    physical: tuple[np.ndarray, np.ndarray],
    parent: tuple[np.ndarray, np.ndarray],
    snapshot: tuple[np.ndarray, np.ndarray],
    claims: Sequence[tuple[np.ndarray, np.ndarray]],
    *,
    y: int,
    rules: Sequence[str],
    allowed: Eligibility,
) -> list[tuple[int, int, int]]:
    """Merge rule claims and reject conflicting or ineligible owners.

    Args:
        physical: Physical row runs with land or water codes.
        parent: Row runs marking the parent's cells.
        snapshot: Owners assigned before this rule group.
        claims: One row of claims for each rule.
        y: Row number for error messages.
        rules: Rule IDs in the same order as claims.
        allowed: Child IDs and the classes they can own.

    Returns:
        (first_column, end_column, owner_id) spans with zero gaps omitted.

    Raises:
        ValueError: A claim is ineligible or two owners claim the same cell.
    """
    starts, ends, values = overlay(physical, parent, snapshot, *claims)
    kind, within, previous, *proposed = values
    invalid_previous = (previous != 0) & (
        (within == 0) | allowed.invalid(previous, kind)
    )
    if invalid_previous.any():
        x = int(starts[np.flatnonzero(invalid_previous)[0]])
        raise ValueError(f"invalid input ownership at {x},{y}")
    owners = previous.copy()
    contributors = np.full(len(starts), -1, dtype=np.int32)
    for index, (rule, new) in enumerate(zip(rules, proposed)):
        active = new != 0
        invalid = active & ((within == 0) | allowed.invalid(new, kind))
        if invalid.any():
            x = int(starts[np.flatnonzero(invalid)[0]])
            raise ValueError(f"rule {rule} assigns an ineligible cell at {x},{y}")
        conflict = active & (owners != 0) & (owners != new)
        if conflict.any():
            pos = int(np.flatnonzero(conflict)[0])
            prior = int(contributors[pos])
            earlier = "input ownership" if prior < 0 else rules[prior]
            raise ValueError(
                f"ownership conflict at {int(starts[pos])},{y}: "
                f"{earlier} -> {int(owners[pos])}; {rule} -> {int(new[pos])}"
            )
        fresh = active & (owners == 0)
        owners[active] = new[active]
        contributors[fresh] = index
    return spans(starts, ends, owners)
