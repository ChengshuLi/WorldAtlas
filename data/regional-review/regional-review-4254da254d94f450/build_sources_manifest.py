#!/usr/bin/env python3
"""Hash exact pinned source bytes and generated evidence extracts for issue #485."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
records=[]
for f in sorted((P/'sources').iterdir()):
 if not f.is_file():continue
 b=f.read_bytes();records.append({'path':'sources/'+f.name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
f=P/'ibc-source-receipt.json';b=f.read_bytes();records.append({'path':f.name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'note':'source restoration metadata; source archive not retained because no open redistribution terms were identified'})
data={'issue':485,'manifest_generated_utc':'2026-10-03','method':'SHA-256 over the exact retained file bytes; gzip digests are over compressed bytes. For downloaded ZIPs, this is the upstream archive byte stream. Uncompressed source-response hashes and derived source IDs/counts are kept in each acquisition receipt/build report.','files':records,'totals':{'file_count':len(records),'retained_bytes':sum(x['bytes'] for x in records),'largest_file_bytes':max((x['bytes'] for x in records),default=0)}}
(P/'sources-manifest.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(data['totals'],indent=2))
