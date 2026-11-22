"""Compare a completed map build with a release on the same grid."""

import argparse
import hashlib
import json
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

from worldatlas.map_build.core.comparison import compare
from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.inputs.releases import cache_release_reference
from worldatlas.map_build.inputs.selection import canonical_bytes
from worldatlas.map_build.inputs.selection_types import MapCodeBinding
from worldatlas.shared.files import JSONValue, read_json, verify_pins
from worldatlas.source_assets.cache import SourceCache


def compare_release(
    run: Path, release: str, output: Path, *, work_dir: Path
) -> dict[str, JSONValue]:
    """Write a cell-change report for a completed build and a release.

    Args:
        run: Completed build directory containing the final grid and input selection.
        release: Official version or numbered release candidate to compare against.
        output: New directory for the report and binary change files.
        work_dir: Workspace whose ``inputs/`` directory caches release files.

    Returns:
        The JSON report with change counts, bounds, and stream checksums.

    Raises:
        ValueError: The build is incomplete, a pinned file changed, or grids differ.
        OSError: A required file cannot be read or the output cannot be created.
    """
    if output.exists():
        raise FileExistsError(f"comparison output already exists: {output}")
    build = read_json(run / "report.json")
    if build.get("status") != "complete":
        raise ValueError("a completed map build is required")

    final = run / "final"
    summary_path = final / "report.json"
    identity_path = run / "run-identity.json"
    verify_pins(
        [
            {"path": str(summary_path), "sha256": build["final"]["report"]["sha256"]},
            {
                "path": str(identity_path),
                "sha256": build["original_run_identity"]["sha256"],
            },
        ]
    )
    grid = Grid(**read_json(summary_path)["grid"])
    selection = read_json(run / "input-selection.json")
    identity = read_json(identity_path)
    if (
        hashlib.sha256(canonical_bytes(selection)).hexdigest()
        != identity["input_selection_sha256"]
    ):
        raise ValueError("the saved geographic selection changed after the build")

    with closing(SourceCache(work_dir / "inputs")) as cache:
        pins = cache_release_reference(release, cache)
    rows, runs = pins["reference_rows"], pins["reference_runs"]
    config = read_json(pins["reference_config"]["path"])
    if grid != Grid(
        width=config["width"], height=config["height"], step=config["step"]
    ):
        raise ValueError("comparison release must use the same grid as the build")
    reference_bindings: list[MapCodeBinding] = [
        {
            "code": category["id"],
            "entity_id": category["entity_id"],
            "physical_class": category["physical_class"],
        }
        for category in config["categories"]
    ]

    # Publish the report and change files together once the build hashes match.
    with TemporaryDirectory(dir=output.parent) as staging:
        pending = Path(staging) / "comparison"
        report = compare(
            final,
            Path(rows["path"]).parent,
            grid,
            pending,
            {"rows.u32le": rows["sha256"], "runs.u32le": runs["sha256"]},
            reference_bindings=reference_bindings,
            candidate_bindings=selection["geography"]["category_bindings"],
        )
        if report["input_sha256"]["candidate"] != {
            f"{name}.u32le": build["final"][name]["sha256"] for name in ("rows", "runs")
        }:
            raise ValueError("final map files changed after the build")
        pending.rename(output)
    return report


def main() -> None:
    """Read command-line options, compare the maps, and print the report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, help="completed build directory")
    parser.add_argument(
        "release", help="official release version or numbered candidate"
    )
    parser.add_argument("output", type=Path, help="new directory for comparison files")
    parser.add_argument(
        "--work-dir",
        type=Path,
        required=True,
        help="workspace with the shared inputs cache",
    )
    args = parser.parse_args()
    try:
        report = compare_release(
            args.run, args.release, args.output, work_dir=args.work_dir
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
