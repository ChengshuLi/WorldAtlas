#!/usr/bin/env python3
"""Stage pinned R2 water shards just in time for build_physical.py."""
import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
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
    def __init__(self, entries, endpoint, log_dir, remove_downloads=False):
        self.entries = entries
        self.endpoint = endpoint
        self.log_dir = Path(log_dir)
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
        src, expected, dest = Path(args[0]).resolve(), str(args[1]), Path(args[2])
        entry = self.entries.get(src)
        if entry is None or entry['sha256'] != expected:
            raise ValueError('shard path or digest not in selected source manifest')
        downloaded = False
        if not src.exists():
            src.parent.mkdir(parents=True, exist_ok=True)
            partial = src.with_name(src.name + '.partial')
            if partial.exists():
                raise FileExistsError(f'partial staging file exists: {partial}')
            physical.download_r2(self.endpoint, entry, partial)
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



class CheckpointStager:
    """Copy validated finished stages into a new build; never alter old outputs."""
    def __init__(self, delegate, checkpoint, events_path, land_report_sha, land_code_sha, shared_code_sha):
        self.delegate = delegate
        self.checkpoint = Path(checkpoint).resolve()
        self.land_report_sha = land_report_sha
        self.land_code_sha = land_code_sha
        self.shared_code_sha = shared_code_sha
        events = [json.loads(line) for line in Path(events_path).read_text().splitlines() if line]
        self.events = {}
        for event in events:
            if event.get('event') == 'shard_complete':
                key = event.get('source_id')
                if key in self.events:
                    raise ValueError('duplicate checkpoint shard event')
                self.events[key] = event

    @staticmethod
    def copy_files(old, new, names):
        new.mkdir()
        for name in names:
            src = old / name
            if src.is_symlink() or not src.is_file():
                raise ValueError(f'missing or symlink checkpoint file: {src}')
            shutil.copyfile(src, new / name)
            if sha(src) != sha(new / name):
                raise ValueError(f'checkpoint copy mismatch: {src}')

    def run_stage(self, name, *args):
        if str(name) == 'rasterize_land.py':
            config, dest = Path(args[0]), Path(args[1])
            old = self.checkpoint / 'land'
            if not old.exists():
                return self.delegate.run_stage(name, *args)
            report = json.loads((old / 'report.json').read_bytes())
            cfg = json.loads(config.read_bytes())
            if (sha(old / 'report.json') != self.land_report_sha or
                    sha(physical.HERE / 'rasterize_land.py') != self.land_code_sha or
                    sha(physical.HERE / 'build.py') != self.shared_code_sha or
                    sha(config) != sha(old / 'config.json') or
                    report.get('configuration_sha256') != sha(config) or
                    report.get('grid') != cfg.get('grid') or report.get('status') != 'candidate-only' or
                    report.get('land_sha256') != sha(old / 'land.tif')):
                raise ValueError('land checkpoint report, config, code or output mismatch')
            for layer in cfg['land']:
                for pin in layer['files']:
                    if sha(Path(pin['path'])) != pin['sha256']:
                        raise ValueError('land input sidecar mismatch')
            self.copy_files(old, dest, ('config.json', 'report.json', 'land.tif'))
            if (sha(dest / 'report.json') != self.land_report_sha or
                    sha(dest / 'config.json') != sha(config) or
                    sha(dest / 'land.tif') != report['land_sha256']):
                raise ValueError('land checkpoint changed during copy')
            for layer in cfg['land']:
                for pin in layer['files']:
                    if sha(Path(pin['path'])) != pin['sha256']:
                        raise ValueError('land input changed during copy')
            self.delegate.record({'event':'reused_land_checkpoint', 'report_sha256':self.land_report_sha,
                                  'producer_code_asserted':self.land_code_sha,
                                  'shared_code_asserted':self.shared_code_sha,
                                  'limitation':'Prior land report does not attest code identity.'})
            return
        if str(name) == 'overture/rasterize_water_shard.py':
            src, source_sha, dest, config = Path(args[0]).resolve(), str(args[1]), Path(args[2]), Path(args[3])
            old = self.checkpoint / 'shards' / dest.name
            if not old.exists():
                return self.delegate.run_stage(name, *args)
            entry = self.delegate.entries.get(src)
            if not entry:
                raise ValueError('checkpoint source not in manifest')
            event = self.events.get(entry.get('source_id'))
            if not event:
                raise ValueError('checkpoint completion event missing')
            report_bytes = (old / 'report.json').read_bytes()
            report_sha = hashlib.sha256(report_bytes).hexdigest()
            report = json.loads(report_bytes)
            cfg = json.loads(config.read_bytes())
            if (report.get('status') != 'candidate-only' or report.get('source_sha256') != source_sha or
                    report.get('source') != str(src) or report.get('configuration_sha256') != sha(config) or
                    report.get('script_sha256') != sha(physical.HERE / name) or
                    report.get('grid') != cfg.get('grid') or report.get('policy') != cfg.get('policy') or
                    report.get('batch_size') != cfg.get('batch_size', 8192) or
                    report.get('output_sha256') != sha(old / 'water.tif') or
                    event.get('sha256') != source_sha or event.get('source') != str(src) or
                    event.get('size') != entry['size'] or
                    event.get('output_sha256') != report.get('output_sha256')):
                raise ValueError(f'shard checkpoint lineage or output mismatch: {src}')
            if report.get('rasterizer') != cfg.get('rasterizer','gdal'):
                raise ValueError('water checkpoint rasterizer/config mismatch')
            names = ('report.json', 'water.tif')
            if report.get('rasterizer') == 'gdal':
                kernel = report.get('gdal_kernel', {})
                if (kernel.get('method') != cfg.get('batch_method','hybrid') or
                        kernel.get('implementation')!='python-gdal-api-v2' or
                        kernel.get('binding_sha256') != sha(physical.HERE/'overture/water_batch.py')):
                    raise ValueError('in-process GDAL water checkpoint mismatch')
            self.copy_files(old, dest, names)
            if sha(dest / 'report.json') != report_sha or sha(dest / 'water.tif') != report['output_sha256']:
                raise ValueError('shard checkpoint changed during copy')
            self.delegate.record({'event':'reused_shard_checkpoint', 'source_id':entry['source_id'],
                                  'source_sha256':source_sha, 'output_sha256':report['output_sha256'],
                                  'report_sha256':report_sha})
            return
        return self.delegate.run_stage(name, *args)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', help='hash-pinned physical pipeline configuration')
    parser.add_argument('output', help='new output directory')
    parser.add_argument('--r2-endpoint', required=True, help='Cloudflare R2 S3 account endpoint')
    parser.add_argument('--log-dir', required=True, help='new directory for staging logs')
    parser.add_argument('--reuse-checkpoint', help='previous incomplete output directory; copy validated completed stages')
    parser.add_argument('--checkpoint-events', help='previous staging events JSONL')
    parser.add_argument('--checkpoint-land-report-sha256', help='asserted digest of previous land report')
    parser.add_argument('--checkpoint-land-code-sha256', help='asserted digest of previous land rasterizer')
    parser.add_argument('--checkpoint-land-shared-code-sha256', help='asserted digest of previous shared build.py')
    parser.add_argument('--remove-completed-downloads', action='store_true',
                        help='remove only newly downloaded temporary shards after successful rasterization')
    args = parser.parse_args()
    entries = manifest_entries(args.config)
    log_dir = Path(args.log_dir).resolve()
    output = Path(args.output).resolve()
    if log_dir == output or log_dir.is_relative_to(output) or output.is_relative_to(log_dir):
        raise ValueError('log and output directories must be separate')
    physical.validate_r2_endpoint(args.r2_endpoint)
    log_dir.mkdir()
    stager = Stager(entries, args.r2_endpoint, log_dir, args.remove_completed_downloads)
    original = physical.run_stage
    if args.reuse_checkpoint:
        checkpoint = Path(args.reuse_checkpoint).resolve()
        if checkpoint == output or checkpoint.is_relative_to(output) or output.is_relative_to(checkpoint):
            raise ValueError('checkpoint and output must be separate')
        if not all((args.checkpoint_events, args.checkpoint_land_report_sha256, args.checkpoint_land_code_sha256, args.checkpoint_land_shared_code_sha256)):
            raise ValueError('checkpoint reuse requires events, land report and land code pins')
        stager = CheckpointStager(stager, args.reuse_checkpoint, args.checkpoint_events,
                                  args.checkpoint_land_report_sha256, args.checkpoint_land_code_sha256,
                                  args.checkpoint_land_shared_code_sha256)
    try:
        physical.run_stage = stager.run_stage
        physical.run(args.config, args.output)
    finally:
        physical.run_stage = original


if __name__ == '__main__':
    main()
