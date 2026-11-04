#!/usr/bin/env python3
"""Find old List 1 evidence leads by diagnostic-span / historical-extent overlap.

A hit is a lead, not a verified source or decision; a miss is not negative evidence.
"""
import argparse
import hashlib
import json
import sqlite3
import shutil
import sys
from pathlib import Path
import cluster
from cluster import digest


def match(cluster_directory, index_path, expected_index_sha, output, minimum_free_bytes=2*1024**3):
    if type(minimum_free_bytes) is not int or minimum_free_bytes < 0: raise ValueError('invalid minimum free space')
    code_sha, dependency_sha = digest(__file__), digest(cluster.__file__)
    cluster_directory, index_path, output = Path(cluster_directory).resolve(), Path(index_path).resolve(), Path(output).resolve()
    report_path = cluster_directory / 'report.json'
    report_raw = report_path.read_bytes()
    report = json.loads(report_raw)
    database = cluster_directory / 'clusters.sqlite'
    if report.get('schema') != 'list1-land-clusters-report-v1' or report.get('status') != 'diagnostic-complete-not-an-override' or digest(database) != report['database_sha256']:
        raise ValueError('cluster report/database integrity failure')
    if digest(index_path) != expected_index_sha:
        raise ValueError('historical evidence index hash mismatch')
    index = json.loads(index_path.read_bytes())
    g = report['identity_inputs']['grid']
    if (index.get('schema') != 'old-list1-evidence-discovery-index-v1'
        or any(float(index['grid'][key]) != float(g[key]) for key in ('width', 'height', 'step', 'west', 'north'))):
        raise ValueError('historical index grid/schema mismatch')
    if output.exists() or output.is_relative_to(cluster_directory) or cluster_directory.is_relative_to(output) or output == index_path or output.is_relative_to(index_path.parent):
        raise ValueError('output must be new and outside input directories')
    output.mkdir(parents=True, exist_ok=False)
    def check_space():
        if shutil.disk_usage(output).free < minimum_free_bytes: raise OSError('free disk space below configured floor')
    check_space()
    # The source is opened read-only. A separate temporary SQLite DB holds leads so
    # the global population is not accumulated in memory.
    db = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)
    leads = sqlite3.connect(output / 'leads.sqlite')
    try:
        leads.execute('CREATE TABLE leads(root INTEGER NOT NULL, item_id TEXT NOT NULL, overlap_cells INTEGER NOT NULL, PRIMARY KEY(root,item_id))')
        items = index['items']
        items_by_id = {item['old_item_id']: item for item in items}
        if len({i['old_item_id'] for i in items}) != len(items):
            raise ValueError('duplicate old item ID')
        for item in items:
            check_space()
            extent = item.get('historical_changed_land_extent')
            if not extent:
                continue
            xs, xe, ys, ye = (extent[k] for k in ('x_start', 'x_end', 'y_start', 'y_end'))
            w, h = g['width'], g['height']
            if any(type(x) is not int for x in (xs, xe, ys, ye)) or not (0 <= xs < w and 0 <= xe < w and 0 <= ys <= ye < h):
                raise ValueError('invalid historical extent')
            ranges = [(xs, xe + 1)] if xs <= xe else [(xs, w), (0, xe + 1)]
            for a, b in ranges:
                q = '''SELECT root, SUM(MIN(end, ?) - MAX(start, ?)) FROM resolved
                       WHERE row BETWEEN ? AND ? AND start < ? AND end > ? GROUP BY root'''
                for root, cells in db.execute(q, (b, a, ys, ye, b, a)):
                    leads.execute('''INSERT INTO leads VALUES (?,?,?)
                        ON CONFLICT(root,item_id) DO UPDATE SET overlap_cells=overlap_cells+excluded.overlap_cells''', (root, item['old_item_id'], cells))
        leads.commit()
        check_space()
        with (output / 'matches.jsonl').open('x') as f:
            for number, (root, cluster_id, cells) in enumerate(db.execute('SELECT root,cluster_id,cells FROM clusters ORDER BY cluster_id')):
                if number % 1000 == 0: check_space()
                candidates = [{'old_item_id': item, 'name': items_by_id[item].get('name'), 'reference': items_by_id[item].get('reference'), 'overlap_with_historical_changed_extent_cells': overlap} for item, overlap in leads.execute('SELECT item_id,overlap_cells FROM leads WHERE root=? ORDER BY item_id', (root,))]
                f.write(json.dumps({'cluster_id': cluster_id, 'cells': cells, 'old_list1_candidates': candidates, 'status': 'unresolved-evidence-review-required'}, sort_keys=True) + '\n')
        if digest(database) != report['database_sha256'] or digest(index_path) != expected_index_sha or report_path.read_bytes() != report_raw or digest(__file__) != code_sha or digest(cluster.__file__) != dependency_sha:
            raise ValueError('input changed during matching')
        result = {'schema': 'old-list1-cluster-discovery-report-v1', 'status': 'diagnostic-only', 'comparison_sha256': report['comparison_sha256'], 'clusters': report['clusters'], 'historical_index_sha256': expected_index_sha, 'cluster_report_sha256': hashlib.sha256(report_raw).hexdigest(), 'matches_sha256': digest(output / 'matches.jsonl'), 'code_sha256': code_sha, 'cluster_code_sha256': dependency_sha, 'limitations': ['Historical changed-land extents are incomplete discovery hints, not source boundaries.', 'A hit is not a verified geographic match; no hit does not establish absence.', 'Inspect old items and their cited source evidence before researching or selecting new decisions.']}
        with (output / 'report.json').open('x') as f:
            json.dump(result, f, sort_keys=True, indent=2)
            f.write('\n')
        return result
    finally:
        db.close()
        leads.close()


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('cluster_directory')
    ap.add_argument('old_list1_index')
    ap.add_argument('old_list1_index_sha256')
    ap.add_argument('output_directory')
    ap.add_argument('--minimum-free-bytes', type=int, default=2*1024**3)
    args = ap.parse_args()
    try:
        print(json.dumps(match(args.cluster_directory, args.old_list1_index, args.old_list1_index_sha256, args.output_directory, args.minimum_free_bytes), indent=2))
    except Exception as exc:
        print('error: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
