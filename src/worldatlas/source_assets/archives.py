"""Select an exact regular-file member from a pinned ZIP archive."""

from pathlib import PurePosixPath
from stat import S_ISLNK
from zipfile import ZipFile, ZipInfo


def archive_member(archive: ZipFile, name: str) -> ZipInfo:
    """Find the single regular file with this exact archive path.

    Args:
        archive: Open ZIP file.
        name: Relative path inside it, such as "data/coast.shp".

    Returns:
        The ZIP entry to open.

    Raises:
        ValueError: The path is invalid or does not name exactly one regular file.
    """
    path = PurePosixPath(name)
    if not name or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"invalid source archive member: {name!r}")
    matches = [item for item in archive.infolist() if item.filename == name]
    if (
        len(matches) != 1
        or matches[0].is_dir()
        or S_ISLNK(matches[0].external_attr >> 16)
    ):
        raise ValueError(
            f"ZIP member must be one regular file. It is missing, duplicated or "
            f"not a regular file: {name!r}"
        )
    return matches[0]
