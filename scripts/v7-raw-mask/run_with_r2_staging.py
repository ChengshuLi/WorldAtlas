#!/usr/bin/env python3
"""Stage pinned R2 water shards just in time for build_physical.py."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading

import build_physical as physical


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(4 << 20), b''):
            h.update(b)
    return h.hexdigest()


def manifest_entries(config_path):
    config = json.loads(Path(config_path).read_bytes())
    source_path, _, source = physical.read_pin(config['source_manifest'])
    files = source.get('files')
    if not isinstance(files, list) or not files or source.get('file_count') != len(files):
        raise ValueError('source manifest must list every shard')
    result = {}
    for e in files:
        rel = Path(e['path'])
        if rel.is_absolute() or '..' in rel.parts:
            raise ValueError('invalid source path')
        path = (source_path.parent / rel).resolve()
        if not path.is_relative_to(source_path.parent) or path in result:
            raise ValueError('duplicate or escaping source path')
        if (not isinstance(e.get('sha256'), str) or len(e['sha256']) != 64 or
                any(c not in '0123456789abcdef' for c in e['sha256']) or
                type(e.get('size')) is not int or e['size'] < 0 or
                not e.get('r2_bucket') or not e.get('r2_key')):
            raise ValueError('invalid source pin or R2 location')
        result[path] = e
    return result


class Stager:
    def __init__(self, entries, wrangler, log_dir, config=None, remove_downloads=False):
        self.entries = entries
        self.wrangler = str(wrangler)
        self.log_dir = Path(log_dir)
        self.config = config
        self.remove_downloads = remove_downloads
        self.lock = threading.Lock()
        self.original_stage = physical.run_stage

    def record(self, event):
        with self.lock:
            with (self.log_dir / 'events.jsonl').open('a') as f:
                f.write(json.dumps(event, sort_keys=True) + '\n')

    def run_stage(self, name, *args):
        if str(name) != 'overture/rasterize_water_shard.py':
            return self.original_stage(name, *args)
        src, expected, _, dest = Path(args[0]).resolve(), str(args[1]), args[2], Path(args[3])
        entry = self.entries.get(src)
        if entry is None or entry['sha256'] != expected:
            raise ValueError('shard path or digest not in selected source manifest')
        downloaded = False
        if not src.exists():
            src.parent.mkdir(parents=True, exist_ok=True)
            partial = src.with_name(src.name + '.partial')
            if partial.exists():
                raise FileExistsError(f'partial staging file exists: {partial}')
            cmd = ['node', self.wrangler, 'r2', 'object', 'get',
                   entry['r2_bucket'] + '/' + entry['r2_key'], '--file', str(partial), '--remote']
            if self.config:
                cmd.extend(['--config', str(self.config)])
            with (self.log_dir / (src.name + '.wrangler.log')).open('xb') as log:
                subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True, env=os.environ.copy())
            if partial.stat().st_size != entry['size'] or sha(partial) != expected:
                raise ValueError(f'R2 size or SHA mismatch: {src}')
            # A hard link fails if a target appeared; never replace another file.
            os.link(partial, src)
            partial.unlink()
            downloaded = True
        if src.stat().st_size != entry['size'] or sha(src) != expected:
            raise ValueError(f'staged size or SHA mismatch: {src}')
        self.original_stage(name, *args)
        report = json.loads((dest / 'report.json').read_bytes())
        if report.get('status') != 'candidate-only' or report.get('source_sha256') != expected:
            raise ValueError(f'incomplete or mismatched shard report: {src}')
        removed = False
        if downloaded and self.remove_downloads:
            # Never remove pre-existing inputs; preserve failed or partial downloads.
            src.unlink()
            removed = True
        self.record({'source_id': entry.get('source_id'), 'path': str(src),
                     'sha256': expected, 'size': entry['size'], 'downloaded': downloaded,
                     'removed_download': removed, 'report': str(dest / 'report.json')})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', help='hash-pinned physical pipeline configuration')
    parser.add_argument('output', help='new output directory')
    parser.add_argument('--wrangler', required=True, help='path to official Wrangler JS entrypoint')
    parser.add_argument('--wrangler-config', help='Wrangler project config, if needed')
    parser.add_argument('--log-dir', required=True, help='new directory for staging logs')
    parser.add_argument('--remove-completed-downloads', action='store_true',
                        help='remove only newly downloaded temporary shards after successful rasterization')
    args = parser.parse_args()
    entries = manifest_entries(args.config)
    log_dir = Path(args.log_dir).resolve()
    output = Path(args.output).resolve()
    if log_dir == output or log_dir.is_relative_to(output) or output.is_relative_to(log_dir):
        raise ValueError('log and output directories must be separate')
    log_dir.mkdir()
    stager = Stager(entries, args.wrangler, log_dir, args.wrangler_config, args.remove_completed_downloads)
    original = physical.run_stage
    try:
        physical.run_stage = stager.run_stage
        physical.run(args.config, args.output)
    finally:
        physical.run_stage = original


if __name__ == '__main__':
    main()
