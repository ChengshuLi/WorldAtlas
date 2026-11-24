"""Define the Unicode nonblank rule used in build inputs and SQL contracts."""

from typing import Annotated

from pydantic import StringConstraints

# Unicode White_Space, expressed as inclusive ranges of code points.
_WHITE_SPACE_RANGES = (
    (0x0009, 0x000D),
    (0x0020, 0x0020),
    (0x0085, 0x0085),
    (0x00A0, 0x00A0),
    (0x1680, 0x1680),
    (0x2000, 0x200A),
    (0x2028, 0x2028),
    (0x2029, 0x2029),
    (0x202F, 0x202F),
    (0x205F, 0x205F),
    (0x3000, 0x3000),
)
UNICODE_WHITESPACE = "".join(
    chr(code) for start, end in _WHITE_SPACE_RANGES for code in range(start, end + 1)
)
# Use explicit Unicode escapes so PostgreSQL and JSON Schema agree.
NONBLANK_PATTERN = (
    "[^"
    + "".join(
        rf"\u{start:04x}" if start == end else rf"\u{start:04x}-\u{end:04x}"
        for start, end in _WHITE_SPACE_RANGES
    )
    + "]"
)
NonEmptyText = Annotated[str, StringConstraints(pattern=NONBLANK_PATTERN)]


def is_nonblank(value: str) -> bool:
    """Check for at least one character outside Unicode White_Space.

    Args:
        value: Text to check.

    Returns:
        True if the text contains a non-whitespace character.
    """
    return bool(value.strip(UNICODE_WHITESPACE))
