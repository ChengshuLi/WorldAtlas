"""General all-center source-coverage selector; no geographic choices.

Call only after the authenticated, single-source polygon rasterizer has rejected
exact boundary/center coincidences and produced per-root hit counts. The caller
must pin source/code/physical/component streams before and after execution and
verify those pins. No V7 labels, old roots, or geographic coordinates enter.
"""
from collections import Counter
from pathlib import Path
from types import MappingProxyType
import polygon_intersection as pi

_COVERAGE_INDEX_TOKEN=object()

class CoverageIndex:
 """Trusted-process cache for one validated generation; not an adversarial snapshot.

 The caller must hash the source streams before and after resolution.
 """
 __slots__ = ('_key', '_totals', '_trusted')
 def __init__(self, key, totals, _token=None):
  if _token is not _COVERAGE_INDEX_TOKEN:raise ValueError('coverage index must be built from validated streams')
  self._key=key;self._totals=MappingProxyType(totals);self._trusted=True

def _stream_key(grid, paths):
 w=grid.get('width');h=grid.get('height')
 if type(w) is not int or type(h) is not int or not 1<w<=1000000 or not 0<h<=1000000:raise ValueError('invalid grid')
 key=[]
 for path in paths:
  p=Path(path).resolve(strict=True);st=p.stat()
  if not p.is_file():raise ValueError('coverage input is not a file')
  key.append((str(p),st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns))
 return (w,h,tuple(key))

def build_coverage_index(grid,physical_rows,physical_runs,component_rows,component_runs):
 paths=(physical_rows,physical_runs,component_rows,component_runs);key=_stream_key(grid,paths);w,h=key[:2];totals=Counter()
 with open(physical_rows,'rb') as pr,open(physical_runs,'rb') as pv,open(component_rows,'rb') as cr,open(component_runs,'rb') as cv:
  for y in range(h):
   physical=pi.readrow(pr,pv,y,w,'physical');components=pi.readrow(cr,cv,y,w,'component');pi.equal_coverage(physical,components,w)
   for a,b,root in components:totals[root]+=b-a
 if _stream_key(grid,paths)!=key:raise ValueError('coverage streams changed during indexing')
 return CoverageIndex(key,totals,_COVERAGE_INDEX_TOKEN)

def indexed_totals(coverage_index,roots,grid,physical_rows,physical_runs,component_rows,component_runs):
 """Return counts for roots from one validated, unchanged stream generation."""
 if type(coverage_index) is not CoverageIndex or getattr(coverage_index,'_trusted',False) is not True:raise ValueError('invalid coverage index')
 paths=(physical_rows,physical_runs,component_rows,component_runs)
 if coverage_index._key!=_stream_key(grid,paths):raise ValueError('coverage index generation mismatch')
 totals={root:coverage_index._totals[root] for root in roots if root in coverage_index._totals}
 if coverage_index._key!=_stream_key(grid,paths):raise ValueError('coverage index generation mismatch')
 return totals

def select_all_centers(inside_counts,grid,physical_rows,physical_runs,component_rows,component_runs,max_roots=1000000,coverage_index=None):
 if not isinstance(inside_counts,dict) or not inside_counts or type(max_roots) is not int or not 0<max_roots<=1000000:raise ValueError('invalid coverage request')
 if len(inside_counts)>max_roots:raise ValueError('root limit exceeded')
 counts={}
 for k,v in inside_counts.items():
  if not isinstance(k,str) or not k.isascii() or not k.isdigit() or (len(k)>1 and k[0]=='0') or type(v) is not int or v<=0:raise ValueError('invalid source hit count')
  root=int(k)
  if not 0<=root<0xffffffff or root in counts:raise ValueError('invalid root')
  counts[root]=v
 w=grid.get('width');h=grid.get('height')
 if type(w) is not int or type(h) is not int or not 1<w<=1000000 or not 0<h<=1000000:raise ValueError('invalid grid')
 if coverage_index is None:
  totals=Counter()
  with open(physical_rows,'rb') as pr,open(physical_runs,'rb') as pv,open(component_rows,'rb') as cr,open(component_runs,'rb') as cv:
   for y in range(h):
    physical=pi.readrow(pr,pv,y,w,'physical');components=pi.readrow(cr,cv,y,w,'component');pi.equal_coverage(physical,components,w)
    for a,b,root in components:
     if root in counts:totals[root]+=b-a
 else:
  if type(coverage_index) is not CoverageIndex or getattr(coverage_index,'_trusted',False) is not True:raise ValueError('coverage index generation mismatch')
  totals=indexed_totals(coverage_index,counts,grid,physical_rows,physical_runs,component_rows,component_runs)
 if set(totals)!=set(counts) or any(counts[r]>totals[r] for r in counts):raise ValueError('source counts exceed or lack component coverage')
 selected=sorted(r for r in counts if counts[r]==totals[r]);partial=sorted(r for r in counts if counts[r]<totals[r])
 if not selected:raise ValueError('no wholly covered components')
 return selected,{'policy':'all-source-cell-centers-v1','selected_count':len(selected),'selected_cells':sum(totals[r] for r in selected),'excluded_partial_count':len(partial),'excluded_partial_cells':sum(totals[r] for r in partial),'excluded_partial_components':[{'component_id_evidence_only':r,'inside_cells':counts[r],'whole_cells':totals[r]} for r in partial], 'limitations':['Requires one source polygon and prior exact boundary-center rejection.','Full component/physical coverage must be authenticated by caller for this generation.','Coverage is geographic evidence, not proof of source rights or historic equivalence.']}
