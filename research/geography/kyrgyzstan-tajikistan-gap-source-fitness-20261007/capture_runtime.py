#!/usr/bin/env python3
"""Capture the exact Python/Shapely runtime bodies used by the bounded producer."""
from __future__ import annotations
import hashlib
import gzip
import io
import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys
import sysconfig
import tarfile

ROOT = pathlib.Path(__file__).resolve().parent
CAPTURE_ROOT = ROOT / "inputs" / "runtime"
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_CAPTURE_BYTES = 128 * 1024 * 1024


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def add_tree(source: pathlib.Path, target_relative: str, files: list[dict]) -> None:
    source = source.resolve()
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        # The bundled runtime contains many unrelated third-party packages. The
        # producer uses the Python standard library plus the separately captured
        # Shapely package; exclude all site-packages from this tree walk.
        if "site-packages" in relative.parts:
            continue
        raw = path.read_bytes()
        if len(raw) > MAX_FILE_BYTES:
            raise ValueError(f"Runtime file exceeds the shared per-file bound: {path}")
        destination = CAPTURE_ROOT / target_relative / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if destination.read_bytes() != raw:
                raise ValueError(f"Captured runtime destination drift: {destination}")
        else:
            with destination.open("xb") as stream:
                stream.write(raw)
        if os.access(path, os.X_OK):
            destination.chmod(path.stat().st_mode & 0o777)
        files.append({
            "path": destination.relative_to(ROOT).as_posix(),
            "source_path": str(path),
            "bytes": len(raw),
            "sha256": sha(raw),
            "role": "python-standard-library-or-native-runtime-file",
        })


def add_file(source: pathlib.Path, target_relative: str, files: list[dict], role: str) -> None:
    source = source.resolve()
    raw = source.read_bytes()
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError(f"Runtime file exceeds the shared per-file bound: {source}")
    destination = CAPTURE_ROOT / target_relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if destination.read_bytes() != raw:
            raise ValueError(f"Captured runtime destination drift: {destination}")
    else:
        with destination.open("xb") as stream:
            stream.write(raw)
    if os.access(source, os.X_OK):
        destination.chmod(source.stat().st_mode & 0o777)
    files.append({"path": destination.relative_to(ROOT).as_posix(),
                  "source_path": str(source), "bytes": len(raw),
                  "sha256": sha(raw), "role": role})


def write_runtime_bundle(files: list[dict]) -> dict:
    """Store the captured runtime as one deterministic, bounded source artifact."""
    target = CAPTURE_ROOT / "runtime-bundle.tar.gz"
    temporary = CAPTURE_ROOT / ".runtime-bundle-incomplete"
    with temporary.open("wb") as raw_stream:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_stream,
                           compresslevel=9, mtime=0) as gzip_stream:
            with tarfile.open(fileobj=gzip_stream, mode="w|") as archive:
                for record in sorted(files, key=lambda item: item["path"]):
                    captured_path = CAPTURE_ROOT / record["path"].removeprefix("inputs/runtime/")
                    raw = captured_path.read_bytes()
                    if len(raw) != record["bytes"] or sha(raw) != record["sha256"]:
                        raise ValueError(f"Captured runtime body changed before bundling: {captured_path}")
                    member_path = record["path"].removeprefix("inputs/runtime/")
                    member = tarfile.TarInfo(member_path)
                    member.size = len(raw)
                    member.mtime = 0
                    member.uid = member.gid = 0
                    member.uname = member.gname = ""
                    member.mode = captured_path.stat().st_mode & 0o777
                    member.type = tarfile.REGTYPE
                    archive.addfile(member, io.BytesIO(raw))
        raw_stream.flush()
        os.fsync(raw_stream.fileno())
    os.replace(temporary, target)
    size = target.stat().st_size
    if size > MAX_FILE_BYTES:
        raise ValueError("Compressed captured runtime exceeds the shared per-file bound")
    raw = target.read_bytes()
    return {"path": target.relative_to(ROOT).as_posix(), "bytes": size,
            "sha256": sha(raw), "format": "deterministic-tar-gzip"}


def main() -> None:
    prefix = pathlib.Path(sys.prefix).resolve()
    stdlib = pathlib.Path(sysconfig.get_paths()["stdlib"]).resolve()
    executable = pathlib.Path(sys.executable).resolve()
    shapely_root = pathlib.Path(__import__("shapely").__file__).resolve().parent
    user_site = shapely_root.parent
    dist_infos = sorted(user_site.glob("shapely-*.dist-info"))
    if len(dist_infos) != 1:
        raise ValueError("Require exactly one installed Shapely distribution metadata directory")
    if not stdlib.is_relative_to(prefix / "lib"):
        raise ValueError("Python standard library is outside the recorded runtime prefix")
    if not shapely_root.name == "shapely":
        raise ValueError("Unexpected Shapely package root")

    files: list[dict] = []
    # Capture Python's full standard library/configuration tree and non-site
    # native libraries, excluding unrelated bundled application packages.
    add_tree(prefix / "lib", "python/lib", files)
    add_file(executable, "python/bin/python3.12", files, "python-interpreter-executable")
    venv_config = prefix / "pyvenv.cfg"
    if venv_config.is_file():
        add_file(venv_config, "python/pyvenv.cfg", files, "python-runtime-configuration")
    add_tree(shapely_root, "python/lib/python3.12/site-packages/shapely", files)
    add_tree(dist_infos[0], "python/lib/python3.12/site-packages/" + dist_infos[0].name, files)
    runtime_site = prefix / "lib/python3.12/site-packages"
    captured_site_root = "python/lib/python3.12/site-packages"
    if (runtime_site / "_distutils_hack").is_dir():
        add_tree(runtime_site / "_distutils_hack", captured_site_root + "/_distutils_hack", files)
    startup_configs = []
    for site_root in (runtime_site, user_site):
        for path in sorted(site_root.iterdir()):
            if (path.is_file() and (path.suffix in (".pth", ".egg-link") or
                                    path.name in ("sitecustomize.py", "usercustomize.py"))):
                if site_root == runtime_site:
                    relative = path.relative_to(runtime_site).as_posix()
                else:
                    relative = path.relative_to(user_site).as_posix()
                add_file(path, captured_site_root + "/" + relative, files,
                         "python-site-startup-configuration")
                startup_configs.append(path.name)

    total = sum(record["bytes"] for record in files)
    if total > MAX_CAPTURE_BYTES:
        raise ValueError("Captured runtime exceeds its 128 MiB admission")
    native = []
    candidates = [CAPTURE_ROOT / record["path"].removeprefix("inputs/runtime/")
                 for record in files if record["path"].endswith((".so", ".dylib"))]
    for path in candidates:
        try:
            report = subprocess.check_output(["otool", "-L", str(path)], text=True,
                                             stderr=subprocess.STDOUT)
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            report = f"unavailable: {type(exc).__name__}: {exc}"
        native.append({"captured_file": path.relative_to(ROOT).as_posix(),
                       "dependency_report": report})

    binary_alias = prefix / "bin" / "python3"
    bundle = write_runtime_bundle(files)
    for record in files:
        record["path"] = record["path"].removeprefix("inputs/runtime/")
    metadata = {
        "version": 1,
        "status": "captured",
        "python": {
            "version": sys.version,
            "implementation": platform.python_implementation(),
            "compiler": platform.python_compiler(),
            "executable_invoked": sys.executable,
            "executable_realpath": str(executable),
            "executable_alias_target": os.readlink(binary_alias) if binary_alias.is_symlink() else None,
            "prefix": str(prefix),
            "stdlib": str(stdlib),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "captured_site_startup_configuration": sorted(set(startup_configs)),
        },
        "spatial_runtime": {
            "shapely_version": __import__("shapely").__version__,
            "geos_version": __import__("shapely").geos_version_string,
            "source_package_path": str(shapely_root),
            "native_modules": ["shapely/lib", "shapely/_geos", "shapely/_geometry_helpers"],
        },
        "projection_runtime": {
            "used": False,
            "reason": "The producer uses literal source GeoJSON coordinates and does not import pyproj or perform a coordinate transformation.",
        },
        "os_runtime": {
            "macos_version": platform.mac_ver()[0],
            "system_dynamic_libraries": [
                "/System/Library/Frameworks/CoreFoundation.framework/Versions/A/CoreFoundation",
                "/usr/lib/libSystem.B.dylib", "/usr/lib/libz.1.dylib",
                "/usr/lib/libedit.3.dylib", "/usr/lib/libncurses.5.4.dylib",
                "/usr/lib/libpanel.5.4.dylib",
                "/System/Library/Frameworks/SystemConfiguration.framework/Versions/A/SystemConfiguration",
            ],
            "note": "Apple system libraries are supplied by the recorded macOS host and are not redistributed; all captured Python/Shapely extension and GEOS library bodies are included below.",
        },
        "captured_bytes": total,
        "captured_file_count": len(files),
        "bundle": bundle,
        "files": files,
        "native_dependency_reports": native,
    }
    manifest = CAPTURE_ROOT / "runtime-manifest.json"
    manifest_bytes = (json.dumps(metadata, sort_keys=True, separators=(",", ":"),
                                 ensure_ascii=False, allow_nan=False) + "\n").encode()
    temporary = manifest.with_name(".runtime-manifest-incomplete")
    with temporary.open("wb") as stream:
        stream.write(manifest_bytes)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, manifest)
    shutil.rmtree(CAPTURE_ROOT / "python")
    print(json.dumps({"status": "captured", "manifest": manifest.relative_to(ROOT).as_posix(),
                      "file_count": len(files), "captured_bytes": total,
                      "manifest_bytes": manifest.stat().st_size,
                      "python": sys.version.split()[0],
                      "shapely": metadata["spatial_runtime"]["shapely_version"],
                      "geos": metadata["spatial_runtime"]["geos_version"]}, sort_keys=True))


if __name__ == "__main__":
    main()
