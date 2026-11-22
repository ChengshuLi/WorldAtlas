"""Supply connections and the recipe snapshot to source constructors."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from psycopg import Connection

from worldatlas.shared.r2 import R2Client


@dataclass(frozen=True)
class Runtime:
    """Give a constructor the resources and record snapshot for one import.

    ``connect`` opens a PostgreSQL connection. ``storage`` provides access
    to raw objects in R2, and ``work_dir`` locates the download cache when
    one is configured. The importer passes this object separately from the
    JSON arguments. ``recipe_id``, ``method``, and ``arguments`` identify
    the record and the settings it used, so shared storage can confirm the
    settings still match when the constructor writes its results.
    """

    connect: Callable[[], Connection]
    storage: R2Client | None
    recipe_id: str
    method: str
    arguments: dict[str, Any]
    work_dir: Path | None = None
