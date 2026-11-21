"""Capture and restore build source bytes without depending on Git history."""

import base64
import gzip
import json
from importlib.metadata import distribution
from pathlib import Path, PurePosixPath
from typing import Any

from worldatlas.shared.files import json_bytes

SCHEMA = "worldatlas-source-code-v1"
SOURCE_SUFFIXES = {
    ".py",
    ".pyi",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".rs",
    ".sh",
    ".sql",
    ".json",
    ".toml",
    ".yml",
    ".yaml",
    ".md",
    ".js",
    ".css",
    ".html",
}
SETUP = ("environment.yml", "pyproject.toml", "README.md")


def capture_source(package: Path | str) -> dict[str, Any]:
    """Capture the Python package and setup files used for this run.

    Args:
        package: Local worldatlas package directory.

    Returns:
        Archive dictionary with "schema" and "files". "files" maps relative
        paths such as "src/worldatlas/__init__.py" to Base64 strings.

    Raises:
        ValueError: A required setup file is missing or an input is a symlink.
    """
    package = Path(package).resolve()
    paths = {
        f"src/worldatlas/{p.relative_to(package).as_posix()}": p
        for p in sorted(package.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts and p.suffix in SOURCE_SUFFIXES
    }
    project = next(
        (
            p
            for p in package.parents
            if (p / "environment.yml").is_file() and (p / "pyproject.toml").is_file()
        ),
        None,
    )
    if project is not None:
        paths.update({name: project / name for name in SETUP})
        paths.update(
            {
                p.relative_to(project).as_posix(): p
                for p in sorted((project / "database").rglob("*.sql"))
            }
        )
    else:
        installed = distribution("worldatlas")
        for item in installed.files or ():
            marker = "share/worldatlas/"
            if marker in item.as_posix():
                relative = item.as_posix().split(marker, 1)[1]
                if relative in SETUP or (
                    relative.startswith("database/") and relative.endswith(".sql")
                ):
                    paths[relative] = Path(str(installed.locate_file(item)))
    if not set(SETUP) <= paths.keys():
        raise ValueError("installed WorldAtlas is missing its build setup files")
    if "database/schema.sql" not in paths:
        raise ValueError("installed WorldAtlas is missing its database schema")
    files = {}
    for name, path in sorted(paths.items()):
        if path.is_symlink():
            raise ValueError("source archive cannot follow a symlink: " + str(path))
        files[name] = base64.b64encode(path.read_bytes()).decode("ascii")
    return {"schema": SCHEMA, "files": files}


def write_source(path: Path | str, content: dict[str, Any]) -> None:
    """Write a new gzip-compressed JSON source archive.

    Args:
        path: Destination. The file must not already exist.
        content: Source archive dictionary.
    """
    with Path(path).open("xb") as output:
        output.write(gzip.compress(json_bytes(content), compresslevel=6, mtime=0))


def read_source(path: Path | str) -> dict[str, Any]:
    """Load and validate a gzip-compressed JSON source archive.

    Args:
        path: Archive file path.

    Returns:
        Archive dictionary with validated file paths and Base64 contents.
    """
    content = json.loads(gzip.decompress(Path(path).read_bytes()))
    source_files(content)
    return content


def source_files(content: dict[str, Any]) -> dict[str, bytes]:
    """Validate every archive path and decode the corresponding file.

    Args:
        content: Archive dictionary with a schema tag and Base64 file values.

    Returns:
        Archive-relative paths mapped to decoded file bytes.

    Raises:
        ValueError: The archive uses an unsafe path, has invalid bytes,
            or is missing required setup files.
    """
    if (
        not isinstance(content, dict)
        or content.get("schema") != SCHEMA
        or not isinstance(content.get("files"), dict)
    ):
        raise ValueError("unsupported source archive")
    files = {}
    for name, encoded in content["files"].items():
        path = PurePosixPath(name)
        if (
            not name
            or not path.parts
            or path.is_absolute()
            or ".." in path.parts
            or "\\" in name
            or path.as_posix() != name
        ):
            raise ValueError("invalid source archive path: " + name)
        try:
            files[name] = base64.b64decode(encoded, validate=True)
        except (TypeError, ValueError) as error:
            raise ValueError("invalid source archive bytes: " + name) from error
    if not {*SETUP, "src/worldatlas/__init__.py"} <= files.keys():
        raise ValueError("source archive is missing package or setup files")
    if any(
        parent.as_posix() in files
        for name in files
        for parent in PurePosixPath(name).parents
    ):
        raise ValueError("source archive path is both a file and a directory")
    return files


def restore_source(content: dict[str, Any], output: Path | str) -> None:
    """Restore the archived files into a new directory.

    Args:
        content: Source archive to validate and extract.
        output: Directory to create for the unpacked copy.

    Raises:
        ValueError: The archive is invalid.
        FileExistsError: The output directory already exists.
    """
    files = source_files(content)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in files.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
