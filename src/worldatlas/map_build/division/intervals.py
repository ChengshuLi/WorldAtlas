"""Vectorized row overlays shared by scope preparation and ownership checks."""

import numpy as np


class Eligibility:
    """Compile child physical eligibility once, including large child sets."""

    def __init__(self, children):
        self.ids = np.asarray(sorted(children), dtype=np.uint32)
        self.kinds = np.asarray(
            [{"mixed": 0, "water": 1, "land": 17}[children[int(e)]] for e in self.ids],
            dtype=np.uint32,
        )
        if not len(self.ids) or self.ids[0] == 0:
            raise ValueError("a division requires positive child IDs")

    def invalid(self, owners, physical):
        positions = np.searchsorted(self.ids, owners)
        safe = np.minimum(positions, len(self.ids) - 1)
        found = (positions < len(self.ids)) & (self.ids[safe] == owners)
        kind = self.kinds[safe]
        return ~found | ((kind != 0) & (kind != physical))


def overlay(*rows):
    """Return aligned [start,end) intervals and each input's value on them."""
    if not rows:
        raise ValueError("an overlay needs at least one row")
    width = int(rows[0][0][-1])
    if any(not len(ends) or int(ends[-1]) != width for ends, _ in rows):
        raise ValueError("overlay rows have different widths")
    cuts = np.unique(np.concatenate(([0], *(ends for ends, _ in rows))))
    starts, ends = cuts[:-1], cuts[1:]
    values = [
        codes[np.searchsorted(stops, starts, side="right")] for stops, codes in rows
    ]
    return starts, ends, values


def spans(starts, ends, values):
    """Coalesce adjacent equal nonzero intervals into ordinary output spans."""
    if not len(starts):
        return []
    changes = np.flatnonzero(np.r_[True, values[1:] != values[:-1]])
    stops = ends[np.r_[changes[1:] - 1, len(ends) - 1]]
    return [
        (int(starts[i]), int(stop), int(values[i]))
        for i, stop in zip(changes, stops)
        if values[i] != 0
    ]


def prepare(physical, parent, selected, snapshot, *, physical_class, unassigned_only):
    """Select output cells once, without modifying geometric or reference context."""
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


def combine(physical, parent, snapshot, claims, *, y, rules, allowed, complete=False):
    """Merge independent claims; an earlier claim can never conceal a conflict."""
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
    if complete and np.any((within != 0) & (owners == 0)):
        x = int(starts[np.flatnonzero((within != 0) & (owners == 0))[0]])
        raise ValueError(f"parent cell has no child owner at {x},{y}")
    return spans(starts, ends, owners)
