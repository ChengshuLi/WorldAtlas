"""Capture and restore build source bytes without depending on Git history."""

import base64
import gzip
from importlib.metadata import distribution
import json
from pathlib import Path, PurePosixPath

from worldatlas.map_build.execution.runtime import json_bytes

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


def capture_source(package):
    """Capture the installed package and its shipped setup files, including local edits."""
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
    else:
        installed = distribution("worldatlas")
        for item in installed.files or ():
            if (
                item.as_posix().endswith("/share/worldatlas/" + item.name)
                and item.name in SETUP
            ):
                paths[item.name] = Path(installed.locate_file(item))
    if not set(SETUP) <= paths.keys():
        raise ValueError("installed WorldAtlas is missing its build setup files")
    files = {}
    for name, path in sorted(paths.items()):
        if path.is_symlink():
            raise ValueError("source archive cannot follow a symlink: " + str(path))
        files[name] = base64.b64encode(path.read_bytes()).decode("ascii")
    return {"schema": SCHEMA, "files": files}


def write_source(path, content):
    with Path(path).open("xb") as output:
        output.write(gzip.compress(json_bytes(content), compresslevel=6, mtime=0))


def read_source(path):
    content = json.loads(gzip.decompress(Path(path).read_bytes()))
    source_files(content)
    return content


def source_files(content):
    """Validate every path before writing any restored source files."""
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


def restore_source(content, output):
    files = source_files(content)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in files.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
