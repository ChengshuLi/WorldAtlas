#!/usr/bin/env python3
"""Find old List 1 evidence leads by diagnostic-span / historical-extent overlap.

A hit is a lead, not a verified source or decision; a miss is not negative evidence.
"""
import argparse
import hashlib
import json
import os
import sqlite3
import shutil
import sys
from pathlib import Path
import cluster
from cluster import digest


def match(cluster_directory, index_path, expected_index_sha, output, expected_report_sha, minimum_free_bytes=2*1024**3, minimum_memory_kib=0, expected_monitor_sha=None):
    if type(minimum_free_bytes) is not int or minimum_free_bytes < 0: raise ValueError('invalid minimum free space')
    if type(minimum_memory_kib) is not int or minimum_memory_kib < 0: raise ValueError('invalid minimum memory')
    if not isinstance(expected_report_sha,str) or len(expected_report_sha)!=64: raise ValueError('expected cluster report hash required')
    code_sha, dependency_sha = digest(__file__), digest(cluster.__file__)
    cluster_directory, index_path, output = Path(cluster_directory).resolve(), Path(index_path).resolve(), Path(output).resolve()
    report_path = cluster_directory / 'report.json'
    def bounded_bytes(path, limit=16*1024*1024):
        with path.open('rb') as f:
            data=f.read(limit+1)
        if len(data)>limit: raise ValueError('oversized JSON input: '+str(path))
        return data
    report_raw = bounded_bytes(report_path)
    if hashlib.sha256(report_raw).hexdigest()!=expected_report_sha: raise ValueError('cluster report hash mismatch')
    report = json.loads(report_raw)
    database = cluster_directory / 'clusters.sqlite'
    monitor_path=cluster_directory/'comparison-monitor.json'
    monitor_raw=None
    if expected_monitor_sha is not None:
        monitor_raw=bounded_bytes(monitor_path)
        if hashlib.sha256(monitor_raw).hexdigest()!=expected_monitor_sha:raise ValueError('comparison monitor hash mismatch')
        monitor=json.loads(monitor_raw)
        if (monitor.get('schema')!='list1-comparison-watchdog-v1' or monitor.get('status')!='sampled-complete'
            or monitor.get('report_sha256')!=expected_report_sha or monitor.get('config_sha256')!=report.get('config_sha256')
            or monitor.get('driver_sha256')!=report.get('code_sha256') or type(monitor.get('samples')) is not int or monitor['samples']<=0
            or type(monitor.get('minimum_memory_kib')) is not int or type(monitor.get('minimum_available_kib')) is not int
            or not monitor['minimum_available_kib']>=monitor['minimum_memory_kib']>0
            or type(monitor.get('peak_process_group_rss_kib')) is not int or type(monitor.get('maximum_process_group_rss_kib')) is not int
            or not 0<monitor['peak_process_group_rss_kib']<=monitor['maximum_process_group_rss_kib']
            or type(monitor.get('sample_interval_seconds')) not in (int,float) or not 0<monitor['sample_interval_seconds']<=.1):
            raise ValueError('comparison monitor binding or resource samples invalid')
    if report.get('schema') != 'list1-land-clusters-report-v1' or report.get('status') not in ('diagnostic-complete-not-an-override','diagnostic-complete-local-policy-unselected') or digest(database) != report['database_sha256']:
        raise ValueError('cluster report/database integrity failure')
    if digest(index_path) != expected_index_sha:
        raise ValueError('historical evidence index hash mismatch')
    index = json.loads(bounded_bytes(index_path))
    g = report['identity_inputs']['grid']
    if (index.get('schema') != 'old-list1-evidence-discovery-index-v1'
        or any(float(index['grid'][key]) != float(g[key]) for key in ('width', 'height', 'step', 'west', 'north'))):
        raise ValueError('historical index grid/schema mismatch')
    if output.exists() or output.is_relative_to(cluster_directory) or cluster_directory.is_relative_to(output) or output == index_path or output.is_relative_to(index_path.parent):
        raise ValueError('output must be new and outside input directories')
    output.mkdir(parents=True, exist_ok=False)
    def sync_dir(path):
        fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
    sync_dir(output.parent)
    def check_space():
        if shutil.disk_usage(output).free < minimum_free_bytes: raise OSError('free disk space below configured floor')
        if minimum_memory_kib:
            available=None
            with open('/proc/meminfo') as f:
                for line in f:
                    if line.startswith('MemAvailable:'):available=int(line.split()[1]);break
            if available is None or available<minimum_memory_kib: raise OSError('available memory below configured floor')
    check_space()
    # The source is opened read-only. A separate temporary SQLite DB holds leads so
    # the global population is not accumulated in memory.
    db = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)
    leads = sqlite3.connect(output / 'leads.sqlite')
    # Keep SQLite spill files off /tmp tmpfs, on the monitored output filesystem.
    for conn in (db,leads):
        conn.execute('PRAGMA temp_store=FILE')
        if conn.execute('PRAGMA temp_store').fetchone() != (1,) or any(row[0]=='TEMP_STORE=3' for row in conn.execute('PRAGMA compile_options')):
            db.close();leads.close();raise OSError('SQLite cannot guarantee file-backed temporary storage')
        quoted=conn.execute('SELECT quote(?)',(str(output),)).fetchone()[0]
        conn.execute('PRAGMA temp_store_directory='+quoted)
        temp_dir=conn.execute('PRAGMA temp_store_directory').fetchone()
        if not temp_dir or Path(temp_dir[0]).resolve()!=output:
            db.close();leads.close();raise OSError('SQLite temporary directory is not the guarded output')
    guard_errors=[]
    def sqlite_guard():
        try: check_space()
        except OSError as exc:
            guard_errors.append(str(exc));return 1
        return 0
    for conn in (db,leads): conn.set_progress_handler(sqlite_guard,10000)
    try:
        leads.execute('CREATE TABLE leads(root INTEGER NOT NULL, item_id TEXT NOT NULL, overlap_cells INTEGER NOT NULL, PRIMARY KEY(root,item_id))')
        items = index['items']
        if not isinstance(items,list) or len(items)>10000 or any(not isinstance(i,dict) or not isinstance(i.get('old_item_id'),str) or not i['old_item_id'] for i in items):
            raise ValueError('invalid historical items or IDs')
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
                f.write(json.dumps({'cluster_id': cluster_id, 'cells': cells, 'old_list1_candidates': candidates, 'status': 'unresolved-evidence-review-required', 'baseline_policy_origin': report.get('baseline_policy_origin'), 'publishable': False}, sort_keys=True) + '\n')
            f.flush();os.fsync(f.fileno())
        sync_dir(output)
        if digest(database) != report['database_sha256'] or digest(index_path) != expected_index_sha or bounded_bytes(report_path) != report_raw or (monitor_raw is not None and bounded_bytes(monitor_path)!=monitor_raw) or digest(__file__) != code_sha or digest(cluster.__file__) != dependency_sha:
            raise ValueError('input changed during matching')
        result = {'schema': 'old-list1-cluster-discovery-report-v1', 'status': ('diagnostic-only-local-policy-unselected' if report.get('baseline_policy_origin') == 'local_unselected_research' else 'diagnostic-only'), 'publishable': False, 'comparison_sha256': report['comparison_sha256'], 'baseline_policy_origin': report.get('baseline_policy_origin'), 'clusters': report['clusters'], 'historical_index_sha256': expected_index_sha, 'cluster_report_sha256': hashlib.sha256(report_raw).hexdigest(), 'matches_sha256': digest(output / 'matches.jsonl'), 'code_sha256': code_sha, 'cluster_code_sha256': dependency_sha, 'limitations': ['Historical changed-land extents are incomplete discovery hints, not source boundaries.', 'A hit is not a verified geographic match; no hit does not establish absence.', 'Inspect old items and their cited source evidence before researching or selecting new decisions.', 'Resource floors are sampled; abrupt external disk or memory use can still exhaust capacity between checks.']}
        result['comparison_monitor_sha256']=expected_monitor_sha
        if monitor_raw is None:result['limitations'].append('No separate comparison monitor was supplied or verified.')
        pending=output/'report.pending';final=output/'report.json'
        with pending.open('x') as f:
            json.dump(result, f, sort_keys=True, indent=2)
            f.write('\n');f.flush();os.fsync(f.fileno())
        linked=False
        try:
            os.link(pending,final);linked=True
            os.unlink(pending);sync_dir(output)
        except OSError as exc:
            if linked: raise OSError('completion marker may exist but durability is uncertain; inspect output before reuse') from exc
            raise
        return result
    except sqlite3.OperationalError as exc:
        if guard_errors: raise OSError(guard_errors[-1]) from exc
        raise
    finally:
        db.close()
        leads.close()


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('cluster_directory')
    ap.add_argument('old_list1_index')
    ap.add_argument('old_list1_index_sha256')
    ap.add_argument('output_directory')
    ap.add_argument('--cluster-report-sha256',required=True)
    ap.add_argument('--comparison-monitor-sha256')
    ap.add_argument('--minimum-free-bytes', type=int, default=2*1024**3)
    ap.add_argument('--minimum-memory-kib',type=int,default=0)
    args = ap.parse_args()
    try:
        print(json.dumps(match(args.cluster_directory, args.old_list1_index, args.old_list1_index_sha256, args.output_directory, args.cluster_report_sha256, args.minimum_free_bytes,args.minimum_memory_kib,args.comparison_monitor_sha256), indent=2))
    except Exception as exc:
        print('error: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
