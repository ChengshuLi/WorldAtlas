#!/bin/sh
# Explicitly restore sources with unresolved redistribution terms for local reproduction.
# Run only after confirming the current provider's terms permit your intended inspection.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source_dir="$here/source"
restore_one() {
  name=$1 url=$2 expected=$3
  output="$source_dir/$name"
  curl --fail --location --silent --show-error "$url" -o "$output.part"
  actual=$(shasum -a 256 "$output.part" | awk '{print $1}')
  if [ "$actual" != "$expected" ]; then
    rm -f "$output.part"
    echo "SHA-256 mismatch for $name: $actual" >&2
    exit 1
  fi
  mv "$output.part" "$output"
  echo "Restored $name ($actual)"
}
case "${1:-}" in
  igvsb)
    restore_one igvsb-municipal-boundaries-2024-provita.zip \
      'https://geoportalp-files.s3-us-east-2.amazonaws.com/files/shapefile/Limites_municipales_de_venezuela_IGVSB_WGS84.zip' \
      'f5c9712ef77a7e4c2692a7c967f7436533b359a4a22cb280e2763b910671991f'
    ;;
  municipal-law)
    restore_one municipal-law.pdf \
      'https://satdc.gobernacion.web.ve/documentos/ordenanzas/ley_organica_del_poder_publico_municipal.pdf' \
      'a6794e9eef64d5d9c13fb47f0783030d1e6337d723eac0a224a397563330aabe'
    ;;
  *) echo "Usage: $0 igvsb|municipal-law" >&2; exit 2 ;;
esac
