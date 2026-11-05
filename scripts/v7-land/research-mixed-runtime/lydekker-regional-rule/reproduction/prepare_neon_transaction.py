"""Build a guarded, insert-or-verify Neon research-record transaction.

This writes SQL to a local file only; it does not access the database.
The caller must use the Neon transaction tool and verify its returned readback.
"""
import hashlib,json,sys
from pathlib import Path
R=Path.cwd();D=R/'regional-lydekker-rule-work';p=D/'selected-regional-policy.json';policy=json.loads(p.read_bytes());assert policy['status']=='selected_for_research' and policy['decision_revision']=='v7-list1-wgs84-draft-170';assert policy['evidence']['pending_inventory_complete'] is False
export=(R/'aegean-archive-containment-integrated-20261105/export-v3-line.local.sql').read_text().strip().rstrip(';').replace('%(revision)s',"'v7-list1-wgs84-draft-170'")
migration=(D/'032_regional_assignment_research.sql').read_text();create,trigger=migration.split('\nDO $$',1);trigger='DO $$'+trigger.strip();assert create.rstrip().endswith(';') and trigger.rstrip().endswith(';')
def q(s):return "'"+s.replace("'","''")+"'"
values=','.join('('+','.join(map(q,[s['source_id'],s['version'],s['sha256']]))+')' for s in policy['sources']);assert len(policy['sources'])==6
# A project-wide advisory lock matches the revision-row guard's own lock.
# Row locks protect the specific line and source assets while snapshot and
# source pins are verified and the selected-for-research record is inserted.
guard=f'''DO $guard$ DECLARE actual_md5 text; n integer; BEGIN
 PERFORM 1 FROM atlas.decision_revisions WHERE revision='v7-list1-wgs84-draft-170' AND status='draft' AND entity_revision='v7-category-bootstrap-v1' FOR SHARE;
 IF NOT FOUND THEN RAISE EXCEPTION 'draft revision missing or changed'; END IF;
 PERFORM 1 FROM atlas.geographic_line_observations WHERE line_id='lydekker-anu-figure81-regional-boo-east-v2' AND geometry_sha256='87514ff08498fa2e2a27bfe2f0a1026511b3c5f01acfbaecbf1f753392c33655' AND md5(geometry::text)='c24a6d68304dc9498dd23adb207b92b5' AND source_id='anu-west-new-guinea-lydekker-ch08' AND source_version='2025-4bcc38d0da4f-official' AND status='research' FOR SHARE;
 IF NOT FOUND THEN RAISE EXCEPTION 'approved line changed'; END IF;
 PERFORM 1 FROM atlas.source_assets s JOIN (VALUES {values}) AS p(source_id,version,sha256) USING(source_id,version,sha256) FOR SHARE OF s;
 SELECT count(*) INTO n FROM atlas.source_assets s JOIN (VALUES {values}) AS p(source_id,version,sha256) USING(source_id,version,sha256);
 IF n<>6 THEN RAISE EXCEPTION 'source catalog pins changed'; END IF;
 SELECT md5(snapshot) INTO actual_md5 FROM ({export}) AS checked_snapshot;
 IF actual_md5 IS DISTINCT FROM 'b4141de32981e3bd1a7e817a92a2424b' THEN RAISE EXCEPTION 'draft snapshot changed'; END IF;
END $guard$;'''
compact=json.dumps(policy,sort_keys=True,separators=(',',':'),ensure_ascii=False);assert '$policy$' not in compact
proof={'policy_file_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'snapshot_export_md5':'b4141de32981e3bd1a7e817a92a2424b','line_geometry_db_md5':'c24a6d68304dc9498dd23adb207b92b5','status':'selected_for_research_not_a_map_or_accepted_geography','pending_inventory_complete':False}; ev=json.dumps(proof,sort_keys=True,separators=(',',':'));assert '$proof$' not in ev
ins=f'''INSERT INTO atlas.regional_island_rule_sets (revision,rule_set_id,selection_status,line_id,definition,evidence) VALUES ('v7-list1-wgs84-draft-170','lydekker-whole-island-regional-v1','selected_for_research','lydekker-anu-figure81-regional-boo-east-v2',$policy${compact}$policy$::jsonb,$proof${ev}$proof$::jsonb) ON CONFLICT (revision,rule_set_id) DO NOTHING;'''
verify=f'''DO $verify$ BEGIN IF NOT EXISTS (SELECT 1 FROM atlas.regional_island_rule_sets WHERE revision='v7-list1-wgs84-draft-170' AND rule_set_id='lydekker-whole-island-regional-v1' AND selection_status='selected_for_research' AND line_id='lydekker-anu-figure81-regional-boo-east-v2' AND definition=$policy${compact}$policy$::jsonb AND evidence=$proof${ev}$proof$::jsonb) THEN RAISE EXCEPTION 'existing research record differs'; END IF; END $verify$;'''
read="SELECT revision,rule_set_id,selection_status,line_id,definition,evidence FROM atlas.regional_island_rule_sets WHERE revision='v7-list1-wgs84-draft-170' AND rule_set_id='lydekker-whole-island-regional-v1'"
output=Path('/tmp/regional-neon-transaction.json');output.write_text(json.dumps({'sql_statements':["SELECT pg_advisory_xact_lock(hashtext('atlas.decision_graph'))",create,trigger,guard,ins,verify,read]}));print('prepared',len(output.read_bytes()),'bytes; policy sha',proof['policy_file_sha256'])
