"""Fail-closed generic root exclusion for independently sourced footprints.

This helper does not authenticate source files or execute a map. Callers must
resolve both the positive full-center containment and the negative polygon
against the same verified component generation. A negative hit on any cell
center excludes that whole component; root numbers are ephemeral results.
"""

def _roots(value, name):
    if not isinstance(value, (list, tuple, set, frozenset)):
        raise ValueError(f"{name} must be a collection")
    result = list(value)
    if any(type(root) is not int or not 0 <= root < 0xFFFFFFFF for root in result):
        raise ValueError(f"{name} has invalid root")
    if len(set(result)) != len(result):
        raise ValueError(f"{name} has duplicate roots")
    return set(result)


def exclude_footprint(fully_contained_roots, negative_hit_roots):
    positive = _roots(fully_contained_roots, "positive roots")
    negative = _roots(negative_hit_roots, "negative roots")
    excluded = positive & negative
    return {
        "selected_roots": sorted(positive - negative),
        "excluded_roots": sorted(excluded),
        "negative_roots_outside_positive": len(negative - positive),
        "limitation": "Any negative-footprint cell-center hit excludes the entire component; input geometry and generation must be independently authenticated.",
    }
