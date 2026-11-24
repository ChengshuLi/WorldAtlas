"""Describe the R2 objects and ZIP members accepted by the source cache."""

from typing import NotRequired

from typing_extensions import TypedDict

from worldatlas.shared.files import ByteCount, Sha256Digest
from worldatlas.shared.text import NonEmptyText


class R2ObjectPin(TypedDict, closed=True):
    """Identify a complete R2 object by location, size, and checksum."""

    r2_bucket: NonEmptyText
    r2_key: NonEmptyText
    sha256: Sha256Digest
    size_bytes: ByteCount
    source_id: NotRequired[NonEmptyText]


class ArchiveMember[Archive](TypedDict, closed=True):
    """Identify one ZIP member and pin the archive that contains it."""

    archive: Archive
    member: NonEmptyText
    sha256: Sha256Digest
    size_bytes: ByteCount


type RemoteFile = R2ObjectPin | ArchiveMember[R2ObjectPin]
