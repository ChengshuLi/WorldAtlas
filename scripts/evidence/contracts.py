"""Independent record and source admission. These checks grant no source approval."""
import math


def exact_rows(rows, expected_ids, key='id', *, allow_empty=False):
    """Validate raw identities before constructing a lossy set/dictionary."""
    if not isinstance(rows, list) or not isinstance(expected_ids, list):
        raise ValueError('Require complete row and authoritative identity lists')
    ids = [row.get(key) if isinstance(row, dict) else None for row in rows]
    for values in (ids, expected_ids):
        if any(not isinstance(value, str) or not value for value in values):
            raise ValueError('Missing or invalid identity')
        if len(values) != len(set(values)):
            raise ValueError('Duplicate raw identities')
    if not allow_empty and not expected_ids:
        raise ValueError('Empty scope cannot establish complete coverage')
    if set(ids) != set(expected_ids):
        raise ValueError('Missing or fabricated identity; incomplete exact scope')
    return dict(zip(ids, rows))


def join_rows(rows, references, fields, *, key='id', reference_key='id'):
    """Compare actual crosswalk fields with independent referenced records."""
    if not fields or not isinstance(fields, dict):
        raise ValueError('Require explicit candidate-to-reference field mapping')
    reference_ids = [row.get(reference_key) for row in references]
    expected = exact_rows(references, reference_ids, reference_key)
    actual = exact_rows(rows, reference_ids, key)
    for identity, row in actual.items():
        for candidate_field, reference_field in fields.items():
            other = expected[identity]
            if candidate_field not in row or reference_field not in other or row[candidate_field] != other[reference_field]:
                raise ValueError('Reference join mismatch: ' + identity + '/' + candidate_field)
    return actual


def finite_metrics(row, required):
    """Missing/null/malformed measurements are not zero or a successful screen."""
    if not isinstance(row, dict) or not required:
        raise ValueError('Require a measurement and explicit required fields')
    for field in required:
        value = row.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError('Missing or nonfinite measurement: ' + field)
    return row


def require_source_text(text, required_fragments):
    """Check retained supporting text, never an HTTP status or URL alone.

    Supply extracted visible/document text. Matching text is not proof of legal
    authority, authenticity, currency or licensing; those still require review.
    """
    if not isinstance(text, str) or not required_fragments or any(
        not isinstance(fragment, str) or not fragment or fragment not in text
        for fragment in required_fragments
    ):
        raise ValueError('Retained source lacks required supporting content')
    return text


def source_crs(crs, *, expected_crs=None):
    """Parse native CRS before any coordinates enter a WGS84-only helper."""
    from pyproj import CRS
    if not crs:
        raise ValueError('Missing native source CRS')
    actual = CRS.from_user_input(crs)
    if expected_crs is not None and not actual.equals(CRS.from_user_input(expected_crs)):
        raise ValueError('Native source CRS differs; select/review a transformation or bounded approximation')
    return actual
