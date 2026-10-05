#!/usr/bin/env python3
"""Independently verify the 39-unit official Istanbul roster join in build_review.py."""
import csv,gzip,json,pathlib,unicodedata
ROOT=pathlib.Path(__file__).parent;SRC=ROOT/'sources'
def norm(s):return ''.join(c for c in unicodedata.normalize('NFKD',s).casefold() if not unicodedata.combining(c) and c.isalnum())
roster=json.load(open(SRC/'istanbul-official-district-roster.json'))['districts']
source=json.load(gzip.open(SRC/'geoBoundaries-TUR-ADM2.geojson.gz','rt'))['features']
index={}
for f in source:index.setdefault(norm(f['properties']['shapeName']),[]).append(f)
alias={'adalar':'princeislands'}
expected=[]
for x in roster:
 key=alias.get(norm(x['name']),norm(x['name'])); hits=index.get(key,[])
 assert len(hits)==1,(x['name'],len(hits))
 expected.append(str(hits[0]['properties']['shapeID']))
rows=list(csv.DictReader(open(ROOT/'istanbul-completeness.csv',newline='')))
assert len(rows)==39 and [x['geoBoundaries_shapeID'] for x in rows]==expected
present=[x for x in rows if x['atlas_baseline_present']=='True']
assert len(present)==7 and all(x['atlas_parent_matches_istanbul_province']=='True' for x in present)
assert len({x['geoBoundaries_shapeID'] for x in rows})==39
print('PASS: 39 official district names map to 39 unique pinned shapeIDs; 7 baseline members, 32 unrepresented candidates.')
