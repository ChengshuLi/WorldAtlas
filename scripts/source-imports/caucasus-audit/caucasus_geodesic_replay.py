"""Replay the approved Caucasus boundary from R2 readbacks and a Neon recipe.

This does not write to Neon or build a map. The caller supplies a local export
of the selected structured recipe and exact R2 source readbacks.
"""
import argparse,hashlib,json,subprocess,sys,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent

def run(name,*args):
 command=[sys.executable,str(HERE/name)]+[str(x) for x in args];print('running',name,flush=True);subprocess.run(command,check=True)
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--recipe',required=True);p.add_argument('--recipe-sha256',required=True);p.add_argument('--r2-readbacks',required=True);p.add_argument('--work-dir',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args();recipe_path=Path(a.recipe).resolve();raw=Path(a.r2_readbacks).resolve();work=Path(a.work_dir).resolve();out=Path(a.output_dir).resolve();work.mkdir(parents=True,exist_ok=False);out.mkdir(parents=True,exist_ok=False);recipe=json.loads(recipe_path.read_text())
 if digest(recipe_path)!=a.recipe_sha256:raise ValueError('selected Neon recipe hash mismatch')
 if recipe.get('schema')!='caucasus-approved-wgs84-recipe-v2':raise ValueError('unsupported recipe')
 stage=work/'sources';run('caucasus_geodesic_prepare.py','--recipe',recipe_path,'--r2-readbacks',raw,'--output',stage)
 selector=work/'selector.json';selector.write_text(json.dumps(recipe['base_selector'],sort_keys=True,separators=(',',':'),allow_nan=False));
 if digest(selector)!=recipe['base_selector_sha256']:raise ValueError('selector digest mismatch')
 with zipfile.ZipFile(raw/'hydro') as z:
  matches=[n for n in z.namelist() if n=='hybas_eu_lev12_v1c.shp' or n.endswith('/hybas_eu_lev12_v1c.shp')]
  if len(matches)!=1:raise ValueError('ambiguous HydroBASINS source')
  shp=work/'hydro.shp';shp.write_bytes(z.read(matches[0]))
 baseline=work/'baseline.json';run('caucasus_selector_replay.py','--recipe',selector,'--recipe-sha256',recipe['base_selector_sha256'],'--shp',shp,'--author',raw/'author','--output',baseline)
 if json.loads(baseline.read_text())['geometry_sha256']!=recipe['baseline_wgs84_sha256']:raise ValueError('baseline geometry mismatch')
 anapa=work/'anapa.json';run('regenerate_anapa_wgs84.py','--baseline',baseline,'--author',raw/'author','--coast',raw/'anapa','--recipe',recipe_path,'--output',anapa)
 abin_osm=work/'abin-merged.osm';run('west_abin_merge_raw_osm.py','--broad',raw/'abin-broad','--further',raw/'abin-further','--ubin',raw/'abin-ubin','--khabl',raw/'abin-khabl','--output',abin_osm)
 abin=work/'anapa-abin.json';abin_report=out/'abin-report.json';run('caucasus_geodesic_abin.py','--recipe',recipe_path,'--osm',abin_osm,'--tile-dir',stage/'original','--baseline',baseline,'--anapa',anapa,'--output',abin,'--report',abin_report)
 run('caucasus_geodesic_models.py','--input',stage,'--recipe',recipe_path)
 output=out/'caucasus-boundary.json';report=out/'replay-report.json';run('caucasus_geodesic_splices.py','--baseline',abin,'--models',stage,'--recipe',recipe_path,'--output',output,'--report',report)
 if digest(output)!=recipe['expected_wgs84_geometry_sha256']:raise ValueError('regenerated geometry mismatch')
 print('verified boundary SHA256',digest(output),flush=True)
if __name__=='__main__':main()
