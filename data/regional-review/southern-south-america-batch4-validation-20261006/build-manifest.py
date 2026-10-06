#!/usr/bin/env python3
"""Build the additive, file-byte-bound evidence manifest for this packet."""
import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[2]
BASELINE = '7245eca6d56ee71fd1f40631c72116167ac5037d'
ISSUE_MARKER = re.compile(r'<!-- worldatlas-work:v1\s*([\s\S]*?)\s*-->')
MANIFEST = 'data/regional-review/southern-south-america-batch4-validation-20261006/evidence-quality.json'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def descriptor(path, raw, role=None):
    row = {'path': path, 'bytes': len(raw), 'sha256': sha(raw), 'hash_kind': 'file-bytes'}
    if role:
        row['role'] = role
    return row


def source(id, url, role, vintage, license_status, terms, restoration, limit):
    return {'id': id, 'url': url, 'role': role, 'vintage': vintage, 'retrieved_at': '2026-10-06',
            'license': {'status': license_status, 'terms': terms}, 'retention': 'restoration-only',
            'verification': 'unverified', 'temporal_status': 'reference',
            'restoration': restoration, 'limit': limit}


def main():
    contract_file = PACKET / 'issue-1116-contract.json'
    issue = json.loads(contract_file.read_text(encoding='utf-8'))
    found = ISSUE_MARKER.search(issue.get('body', ''))
    if not found:
        raise ValueError('issue-1116-contract.json lacks worldatlas-work:v1')
    contract = json.loads(found.group(1))
    quality = contract['evidence_quality']
    ids = quality['subject_ids']
    expected_path = 'data/regional-review/southern-south-america-batch4-validation-20261006/'
    if issue.get('number') != 1116 or quality.get('manifest_path') != expected_path + 'evidence-quality.json':
        raise ValueError('Issue number or manifest path changed')
    if len(ids) != 215 or len(set(ids)) != 215:
        raise ValueError('Issue subject inventory changed')

    pins = quality['pins']
    pin_files = {
        'world-index': 'data/world-index.json',
        'hierarchy': 'data/hierarchy.json',
        'original-scope': 'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/scope/embedded-workload-scope.json',
        'original-crosswalk': 'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/crosswalk.csv',
        'original-reproducer': 'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/reproduce.py',
        'original-manifest': 'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/evidence-quality.json',
        'original-summary': 'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/reproduction-summary.json',
        'original-source-register': 'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/source/source-register.json',
    }
    if set(pins) != set(pin_files):
        raise ValueError('Issue pins differ from expected exact baseline files')
    input_paths = [
        'data/world-index.json', 'data/hierarchy.json',
        'data/geography/part-2.json', 'data/geography/part-20.json', 'data/geography/part-28.json',
        'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/scope/embedded-workload-scope.json',
        'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/crosswalk.csv',
        'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/province-review.csv',
        'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/area-review.csv',
        'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/evidence-quality.json',
        'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/source/source-register.json',
        'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/source/geoBoundaries-CHL-ADM3-metaData.json',
        'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/source/geoBoundaries-PRY-ADM2-metaData.json',
        'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/reproduce.py',
        'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/reproduction-summary.json',
        'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/source-review.md',
    ]
    baseline_files = []
    baseline_raw = {}
    for path in input_paths:
        raw = subprocess.check_output(['git', '-C', str(REPO), 'show', BASELINE + ':' + path])
        baseline_raw[path] = raw
        baseline_files.append(descriptor(path, raw))
    for name, path in pin_files.items():
        if sha(baseline_raw[path]) != pins[name]:
            raise ValueError('Issue pin differs from immutable bytes: ' + name)

    audit_path = expected_path + 'run-one/crosswalk-baseline-audit.json'
    audit = json.loads((REPO / audit_path).read_text(encoding='utf-8'))
    positive_path = expected_path + 'run-one/positive-control.json'
    negative_path = expected_path + 'run-one/negative-controls.json'
    two_path = expected_path + 'two-run-reproducibility.json'
    positive = json.loads((REPO / positive_path).read_text(encoding='utf-8'))
    negative = json.loads((REPO / negative_path).read_text(encoding='utf-8'))
    two = json.loads((REPO / two_path).read_text(encoding='utf-8'))
    if audit.get('scope_id_count') != 215 or audit.get('baseline_feature_matches') != 215 or audit.get('distinct_actual_parent_count') != 39:
        raise ValueError('Audit output differs from expected issue scope')
    if negative.get('controls_executed') != 9 or not all(row.get('outcome') == 'rejected' for row in negative['controls']):
        raise ValueError('Negative control set is incomplete')
    if positive.get('outcome') != 'passed' or two.get('outcome') != 'passed' or two.get('run_one_sha256') != two.get('run_two_sha256'):
        raise ValueError('Positive or two-run control failed')

    outputs = []
    for file in sorted(PACKET.rglob('*')):
        if not file.is_file() or file.name == 'evidence-quality.json' or '__pycache__' in file.parts or file.suffix == '.pyc':
            continue
        if file.is_symlink():
            raise ValueError('Symlink output is not allowed')
        path = file.relative_to(REPO).as_posix()
        raw = file.read_bytes()
        role = 'code' if path.endswith('.py') else 'documentation' if path.endswith('.md') else 'generated-result'
        if path.endswith('.json') and ('issue' in file.name or 'snapshots' in file.name):
            role = 'source-snapshot'
        outputs.append(descriptor(path, raw, role))

    evidence_sources = [
        source('gb-chl-adm3-2020', 'https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/CHL/ADM3/geoBoundaries-CHL-ADM3.geojson',
               'Chile ADM3 commune source represented in retained metadata', '2020; source commit 9469f09592ced973a3448cf66b6100b741b64c0d', 'redistributable',
               'Retained geoBoundaries metadata records CC BY 3.0 IGO and attribution. Original source bytes are not retained; metadata/hash were inspected.',
               'Restore the exact URL at commit 9469f09592ced973a3448cf66b6100b741b64c0d; verify 171783952 decompressed bytes and SHA-256 f3833ce1965394ae705e3793b50bdd007775b43da604251871deffed04f3bffd, then parse properties.shapeID/shapeName.',
               'Full source rows, current official authority, completeness, legal parenthood and boundaries were not reverified; file exceeds the 32 MiB decompressed input cap.'),
        source('gb-pry-adm2-2012', 'https://github.com/wmgeolab/geoBoundaries/raw/f549eab/releaseData/gbOpen/PRY/ADM2/geoBoundaries-PRY-ADM2.geojson',
               'Paraguay ADM2 district source represented in retained metadata', '2012; source commit f549eab25a258603ea32c9dc6cb11b7657796478', 'redistributable',
               'Retained geoBoundaries metadata records CC BY 4.0 and attribution. Original source bytes are not retained; metadata/hash were inspected.',
               'Restore the exact URL at commit f549eab25a258603ea32c9dc6cb11b7657796478; verify 45589273 decompressed bytes and SHA-256 d42bd1f910070bf805e32dc46708230c91f58902a3c8792eda60928b22362858, then parse properties.shapeID/shapeName.',
               'Full source rows, current district authority, completeness, legal parenthood and boundaries were not reverified; file exceeds the 32 MiB decompressed input cap.'),
        source('paraguay-ine-2022-attributes', 'https://geonode.ine.gov.py/geoserver/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=geonode%3ADistritos_Paraguay_INE_2022_conID&propertyName=DPTO%2CDPTO_DESC%2CDISTRITO%2CDIST_DESC_%2CCLAVE%2Cid&outputFormat=application%2Fjson&srsName=EPSG%3A4326',
               'Paraguay INE 2022 statistical row-name/code/department reference; no geometry', 'Layer metadata published 2024-07-05; response retrieved 2026-10-05 per inherited source register', 'unknown',
               'Inherited source register says public information with attribution; currently viewed INE GeoNode metadata says Public Domain. Response-specific reuse terms are unresolved.',
               'Restore the exact attribute-only WFS response; verify 55137 bytes and SHA-256 3cf026dd552ac4128f97b68acbdb8e06aba08afdde13fa208185cb07447ae228 before comparing all 47 recorded names/codes/departments.',
               'Current INE layer metadata says the boundaries are approximate, non-legal and statistical only. Exact response bytes and its rows were not reverified.'),
        source('subdere-chile-dpa-2023', 'https://www.subdere.gov.cl/sala-de-prensa/subdere-publica-nueva-versi%C3%B3n-de-los-l%C3%ADmites-de-la-divisi%C3%B3n-pol%C3%ADtico-administrativa',
               'Official Chile DPA source notice and restoration lead', '2023 release notice dated 2023-11-10', 'unknown',
               'The linked 2023 archive has no explicit reuse terms located in the inherited review; no archive bytes are retained.',
               'The notice links https://ide.subdere.gov.cl/descargas/SHP/Limite_DPA_03082023.rar; inherited record says 262380302 bytes, SHA-256 4c8dd01ca4ca7d8b111dac78b88cc8ac64c1af7b8ebe0c85a21eaab337ae3fd3, retrieved 2026-10-05. Obtain reuse terms and a RAR5-capable extraction path before polygon comparison.',
               'Official page establishes the publication and agency workflow only. The archive was not extracted, matched to subjects or independently licensed.'),
        source('paraguay-cadastre-district-study', 'https://www.catastro.gov.py/site/47/Estudio-de-Limites-Distritales-de-la-Republica-del-Paraguay_V2023',
               'National Cadastre legal-boundary uncertainty context, not a polygon source', 'Official page identifies January 2024 ongoing study; viewed 2026-10-06', 'unknown',
               'No PDF reuse terms were located in the inherited review; the report is not retained.',
               'The original register records https://www.catastro.gov.py/public/967e7c_ESTUDIO%20DE%20L%C3%8DMITES%20DISTRITALES%20DE%20LA%20REP%C3%9ABLICA%20DEL%20PARAGUAY.pdf as 4079648 bytes, SHA-256 c07fd97db9ee7063e377dd6df14f032847c16296a9c8354fe1179d3203762bd1, retrieved 2026-10-05. Confirm that the current official page serves those exact bytes before relying on the prior hash.',
               'The official page supports a national ongoing review of legal uncertainty, not a row-level legal conclusion for these 47 IDs.'),
        source('tdwg-wgsrpd-level3-level4', 'https://github.com/tdwg/wgsrpd/tree/52da7828aba9d461dd133c27b3bd7a4407161f54/109-488-1-ED/2nd%20Edition',
               'Historical botanical distribution area/scale crosswalk preserved from PR #948', 'WGSRPD 2nd Edition tables at commit 52da7828aba9d461dd133c27b3bd7a4407161f54', 'unknown',
               'Inherited review found no table reuse terms; exact table files remain restoration-only.',
               'Restore tblLevel3.txt (9933 bytes, SHA-256 7eaf281dfbdca610c93938326c333d7c62d8e82ce3cba63b299d5a3a01d0003f) and tblLevel4.txt (17137 bytes, SHA-256 6fa350a0bb5939df0c665ae6cf253ddb0aa85fef6daa684c87ba400faf93b1c2) from the pinned commit; verify bytes before rerunning the inherited name/scale crosswalk.',
               'The inherited table comparison is not rerun here and botanical Level 3/4 units are not administrative parent/child proof.'),
        source('natural-earth-asuncion-aggregate', 'https://github.com/nvkelso/natural-earth-vector/tree/ca96624a56bd078437bca8184e78163e5039ad19',
               'Source citation carried by the retained Asunción Atlas aggregate', 'Undated modern reference in baseline feature metadata', 'unknown',
               'Retained metadata describes Natural Earth-derived source material as public domain, but exact source file/vintage and constituent row were not restored.',
               'The retained Atlas feature cites Natural Earth and four 2012 district source member IDs. No exact source product, query or extraction hash is identified by this corrective scope; obtain a pinned reproducible source row before adjudicating entity/extent.',
               'Source identity, legal tier, completeness, extent, overlap and parent remain unresolved.'),
    ]

    output_by_path = {row['path']: row for row in outputs}
    audit_hash = output_by_path[audit_path]['sha256']
    negative_hash = output_by_path[negative_path]['sha256']
    metric_specs = [
        ('exact_issue_subjects', 215, 'subjects', audit_path, '/scope_id_count'),
        ('baseline_feature_matches', 215, 'features', audit_path, '/baseline_feature_matches'),
        ('baseline_member_id_name_matches', 214, 'candidate baseline metadata pairs', audit_path, '/source_profile_counts/retained-baseline-member-ID-name matches'),
        ('upstream_feature_rows_reverified', 0, 'external source rows', audit_path, '/source_profile_counts/independently reverified upstream source rows'),
        ('actual_province_parent_ids', 39, 'parents', audit_path, '/distinct_actual_parent_count'),
        ('negative_controls_rejected', 9, 'controls', negative_path, '/controls_executed'),
        ('ine_response_rows_reverified', 0, 'rows', audit_path, '/source_profile_counts/Paraguay INE response bytes independently reverified'),
        ('area_scope_records_validated', 5, 'areas', audit_path, '/area_records_preserved_and_checked'),
    ]
    metrics, metric_bindings, summaries = [], [], []
    for mid, value, unit, path, pointer in metric_specs:
        input_hash = output_by_path[path]['sha256']
        metrics.append({'id': mid, 'value': value, 'unit': unit, 'vintage': 'baseline',
                        'evaluation_commit': BASELINE, 'input_sha256': input_hash})
        metric_bindings.append({'metric_id': mid, 'path': path, 'json_pointer': pointer})
        summaries.append({'metric_id': mid, 'value': value, 'unit': unit})

    rows = []
    for row in outputs:
        rows.append({'path': row['path'], 'status': 'added'})
    rows.append({'path': MANIFEST, 'status': 'added'})
    # New-file receipts deliberately omit previous_path: GitHub has no previous_filename for additions.
    method_id = 'southern-south-america-crosswalk-baseline-audit'
    manifest = {
        'version': 1,
        'issue': 1116,
        'lane': 'geography',
        'worker_id': '01a10947-7d6e-7ba2-98a1-a9f91dedabfc',
        'subject_ids': ids,
        # Match evidence-quality.mjs subjectsHash: compact JSON of sorted IDs.
        'subject_ids_sha256': sha(json.dumps(sorted(ids), separators=(',', ':')).encode('utf-8')),
        'baseline': {
            'commit': BASELINE,
            'files': baseline_files,
            'pins': pins,
            'pin_files': pin_files,
            'subject_files': {row['subject_id']: row['baseline_file'] for row in audit['row_audit']},
        },
        'sources': evidence_sources,
        'outputs': outputs,
        'methods': [{
            'id': method_id,
            'kind': 'generator',
            'helper_version': 'worldatlas-evidence-preparation-v1',
            'description': 'Compare exact #1116 candidate subject/crosswalk/parent/area rows to immutable #935 baseline feature identities and metadata; execute negative corruption controls and reproduce the legacy false positive without restoring oversized source files.',
            'software': 'Python 3.12.14 standard library; verify-packet.py; committed Git objects; no external packages or network requests',
            'units': 'issue-scoped feature rows, parent IDs, area records and crosswalk source-member metadata',
        }],
        'metrics': metrics,
        'summaries': summaries,
        'metric_bindings': metric_bindings,
        'validation': [
            {'method_id': method_id, 'kind': 'positive-control', 'outcome': 'passed', 'evidence_path': positive_path},
            {'method_id': method_id, 'kind': 'negative-control', 'outcome': 'passed', 'evidence_path': negative_path},
            {'method_id': method_id, 'kind': 'reproducibility', 'outcome': 'passed', 'evidence_path': two_path},
        ],
        'change_receipts': rows,
        'conclusions': [
            {'text': 'All 215 issue subjects and their 39 stored Atlas province-parent identities match the exact immutable baseline; this checks retained Atlas identity/parent links only.', 'status': 'supported', 'source_ids': ['gb-chl-adm3-2020', 'gb-pry-adm2-2012']},
            {'text': '214 candidate source-member ID/name pairs agree with retained baseline metadata, but zero upstream source feature rows were independently reverified in this packet.', 'status': 'supported', 'source_ids': ['gb-chl-adm3-2020', 'gb-pry-adm2-2012']},
            {'text': 'The original source originals exceed the decompressed evidence file limit; current source completeness, legal parentage and boundaries remain unresolved.', 'status': 'unresolved', 'source_ids': ['gb-chl-adm3-2020', 'gb-pry-adm2-2012', 'subdere-chile-dpa-2023', 'paraguay-cadastre-district-study']},
            {'text': 'The 47 INE candidate attributes are statistical-only and their exact response bytes and applicable response-level reuse terms remain unresolved.', 'status': 'unresolved', 'source_ids': ['paraguay-ine-2022-attributes']},
            {'text': 'The Asunción aggregate source identity, legal tier, extent and parent remain unresolved.', 'status': 'unresolved', 'source_ids': ['natural-earth-asuncion-aggregate']},
            {'text': 'Five inherited macro-area labels have a historical botanical scale crosswalk, not administrative equivalence or boundary evidence.', 'status': 'unresolved', 'source_ids': ['tdwg-wgsrpd-level3-level4']},
        ],
        'stages': {'research': 'complete', 'implementation': 'proposed', 'geographic_approval': 'unapproved'},
        'commands': [
            'python3 data/regional-review/southern-south-america-batch4-validation-20261006/verify-packet.py --out-dir run-one',
            'python3 data/regional-review/southern-south-america-batch4-validation-20261006/verify-packet.py --out-dir run-two',
        ],
        'limits': [
            'The 2020 Chile and 2012 Paraguay geoBoundaries originals are not retained or restored here; source IDs/names were compared with retained baseline metadata only.',
            'The 2022 Paraguay INE response is unretained; no response row or response-level license term was reverified. The official layer is statistical-only and non-legal.',
            'The current INE GeoNode layer displays Public Domain, while the inherited response record says attribution-required public information; preserve this response-level license conflict.',
            'The official SUBDERE 2023 archive was not extracted and no reuse permission was found in the inherited review; no Chile current geometry was compared.',
            'The Cadastre PDF and WGSRPD tables remain restoration-only; their prior file-byte hashes were not re-fetched in this packet.',
            'Baseline parent and area consistency does not establish current administrative role, lawful parentage, boundary completeness, positional accuracy, neighboring seam consistency or regional approval.',
            'The Natural Earth-derived Asunción aggregate lacks an exact retained source-product/row restoration pin; its legal unit identity and extent remain unresolved.',
        ],
    }
    path = PACKET / 'evidence-quality.json'
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'manifest': path.as_posix(), 'outputs': len(outputs), 'baseline_files': len(baseline_files),
                      'source_records': len(evidence_sources), 'metrics': len(metrics), 'change_receipts': len(rows),
                      'audit_sha256': audit_hash, 'negative_controls_sha256': negative_hash}, indent=2))


if __name__ == '__main__':
    main()
