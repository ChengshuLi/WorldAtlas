#!/usr/bin/env bash
set -euo pipefail

version=0.3.4
if ! pg_config=$(command -v "${1:-pg_config}"); then
    echo "Put pg_config on PATH or pass its absolute path." >&2
    exit 1
fi
pg_config="$(cd "$(dirname "$pg_config")" && pwd)/$(basename "$pg_config")"
lib_dir=$("$pg_config" --pkglibdir)
extension_dir=$("$pg_config" --sharedir)/extension
control="$extension_dir/pg_jsonschema.control"
sql_file=pg_jsonschema--$version.sql

platform=$(uname -s)
if [[ "$platform" == Darwin ]]; then
    suffix=dylib
else
    suffix=so
fi
library=pg_jsonschema.$suffix

if [[ -f "$control" ]]; then
    installed_version=$(awk -F "'" '$1 ~ /^[[:space:]]*default_version[[:space:]]*=/ {print $2; exit}' "$control")
    if [[ "$installed_version" != "$version" ]]; then
        printf 'pg_jsonschema already uses version %s in %s. Use a separate PostgreSQL install for %s.\n' \
            "${installed_version:-unknown}" "$extension_dir" "$version" >&2
        exit 1
    fi
    if [[ -f "$lib_dir/$library" && -f "$extension_dir/$sql_file" ]]; then
        printf 'Using pg_jsonschema %s in %s\n' "$version" "$extension_dir"
        exit 0
    fi
fi

scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
pg_version=$("$pg_config" --version)
pg_major=${pg_version#PostgreSQL }
pg_major=${pg_major%%.*}
release=https://github.com/supabase/pg_jsonschema/releases/download/v$version

case "$platform" in
    Darwin)
        curl -fsSL --retry 3 "https://codeload.github.com/supabase/pg_jsonschema/tar.gz/refs/tags/v$version" -o "$scratch/source.tar.gz"
        mkdir "$scratch/source"
        tar -xzf "$scratch/source.tar.gz" -C "$scratch/source" --strip-components=1
        export PGRX_HOME="$scratch/pgrx"
        export SDKROOT="$(xcrun --show-sdk-path)"
        export LIBCLANG_PATH="$(dirname "$(xcrun --find clang)")/../lib"
        cargo install --locked --version 0.16.1 --root "$scratch/tools" cargo-pgrx
        export PATH="$scratch/tools/bin:$PATH"
        cargo pgrx init "--pg$pg_major" "$pg_config"
        (
            cd "$scratch/source"
            cargo pgrx package --pg-config "$pg_config" --out-dir "$scratch/package"
        )
        package_lib="$scratch/package$lib_dir"
        package_extension="$scratch/package$extension_dir"
        ;;
    Linux)
        arch=$(dpkg --print-architecture)
        curl -fsSL --retry 3 "$release/pg_jsonschema-v$version-pg$pg_major-$arch-linux-gnu.deb" -o "$scratch/extension.deb"
        dpkg-deb --extract "$scratch/extension.deb" "$scratch/package"
        package_lib="$scratch/package/usr/lib/postgresql/$pg_major/lib"
        package_extension="$scratch/package/usr/share/postgresql/$pg_major/extension"
        ;;
    *)
        echo "Use a PostgreSQL installation with pg_jsonschema $version available." >&2
        exit 1
        ;;
esac

install -m 755 "$package_lib/$library" "$lib_dir/"
install -m 644 "$package_extension/$sql_file" "$package_extension/pg_jsonschema.control" "$extension_dir/"
printf 'Installed pg_jsonschema %s in %s\n' "$version" "$extension_dir"
