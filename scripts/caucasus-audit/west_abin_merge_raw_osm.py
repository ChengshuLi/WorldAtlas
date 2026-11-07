"""Reproduce the Abin research model's merged OSM input from raw archives.

The merge preserves source object order and rejects conflicting objects. It
does not select a boundary, prove flow direction or write to Neon.
"""
import argparse
import hashlib
import io
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

PINS = {
    'broad': 'ada68ef47c11ad4cfbdcd36cf369ca96e91072cfd406f2d28f2f16349dc4b72d',
    'further': '7152fe44f0dae950965c06777e206a396f3b7938ee1fdc4d33dc0f96757e0033',
    'ubin': '2e2bbebd62e0c5bbca7c2ca9ebc00bb263dec148d26c922db5cdc619764be216',
    'khabl': '42864b4776eecd500c639c72028ff2eec2b16f9454215d1c9a42acc194060e50',
}
MERGED = '430a7eb2165a500c165ec752a7681ee81292b2d6ea0c6efdaf0292427e4dc1f9'


def sha(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def signature(element):
    return (element.tag, tuple(sorted(element.attrib.items())),
            tuple(signature(child) for child in element))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('broad', 'further', 'ubin', 'khabl', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    if Path(args.output).exists():
        raise FileExistsError(args.output)
    for name, digest in PINS.items():
        if sha(getattr(args, name)) != digest:
            raise ValueError('OSM input hash mismatch: ' + name)
    sources = [Path(args.broad).read_bytes(), Path(args.further).read_bytes()]
    for archive_name, names in [('ubin', ('west-north-a.osm', 'west-north-b.osm')),
                                ('khabl', ('west-habl-a.osm', 'west-habl-b.osm',
                                           'west-north-node-890704144.osm', 'west-north-node-890704520.osm'))]:
        with zipfile.ZipFile(getattr(args, archive_name)) as archive:
            for name in names:
                if archive.namelist().count(name) != 1:
                    raise ValueError('missing or ambiguous archive member: ' + name)
                sources.append(archive.read(name))
    root = ET.Element('osm', {'version': '0.6'})
    seen = {}
    for data in sources:
        for element in ET.parse(io.BytesIO(data)).getroot():
            if element.tag not in {'node', 'way', 'relation'}:
                continue
            key = (element.tag, element.get('id'))
            if not key[1] or not element.get('version'):
                raise ValueError('OSM object lacks an id or version')
            sig = signature(element)
            if key in seen:
                if sig != seen[key]:
                    raise ValueError('conflicting OSM object: ' + '/'.join(key))
                continue
            seen[key] = sig
            root.append(element)
    # Serialize before writing the requested output so hash failure leaves no
    # candidate file. ET's serialization and the fixed source order are pinned.
    out = io.BytesIO()
    ET.ElementTree(root).write(out, encoding='utf-8', xml_declaration=True)
    data = out.getvalue()
    if hashlib.sha256(data).hexdigest() != MERGED:
        raise ValueError('merged OSM bytes differ from the pinned research input')
    for name, digest in PINS.items():
        if sha(getattr(args, name)) != digest:
            raise ValueError('OSM input changed during merge: ' + name)
    with open(args.output, 'xb') as f:
        f.write(data)
    print('merged_sha256', MERGED, 'objects', len(seen))


if __name__ == '__main__':
    main()
