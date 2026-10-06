#!/usr/bin/env python3
"""Read exact classified pixels intersecting the two retained seam fragments."""
import hashlib, json, urllib.request, time, subprocess, sys
from pathlib import Path
import numpy as np
import rasterio
from rasterio.mask import mask
from shapely.geometry import shape, mapping, box
from shapely.ops import transform
from pyproj import Transformer
ROOT=Path(__file__).resolve().parents[4]
PACKET=ROOT/"research/geography/shared-seam-ind-pak-20261006"
OUT=PACKET/"follow-up-v2"
CACHE=PACKET/".cache/worldcover-2021-v200"
BASE="https://esa-worldcover.s3.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_{}_Map.tif"
TILES=["N27E069","N27E072","N30E069","N30E072"]
EXPECTED={
 "N27E069":(105024722,"f023ee9f015c9382dcf312c68b0133f42d0cebb72ba5f48c23a646b37b7becda","\"39e8b075d5a0e635c191d03c547fdf98-13\""),
 "N27E072":(108754189,"d5701719d5f34ad89ab56feb5eeb873eb1468535b9b1e3d280ce4253955e0ff7","\"bb4d52dce7d39d4ec21ae1a3cdaabb0d-13\""),
 "N30E069":(150596996,"393c2c77ee3c001b91c7094ec4013d9365500ab2bfbc4eb1e48416a0757d05ee","\"e0fd9757315ad1e3e425070bf6f8c9f9-18\""),
 "N30E072":(122839390,"54c7fcb36c475831bc74767a817f3221b4058d4f05cde4a86181ed83f072e957","\"b4c7d164e8a9950c2078c47e2958f6d2-15\""),
}
RELEASED="2022-10-28"

def sha(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for b in iter(lambda:f.read(8*1024*1024),b""): h.update(b)
 return h.hexdigest()
def read_json(path): return json.loads(path.read_text())
def fragment_digest(feature):
 return hashlib.sha256((json.dumps(feature,ensure_ascii=False,sort_keys=False,separators=(",",":"))+"\n").encode()).hexdigest()
def main():
 CACHE.mkdir(parents=True,exist_ok=True)
 fragments={}; fragment_hashes={}
 for p in (PACKET/"sources/physical-gap-fragments").glob("*.geojson"):
  f=read_json(p); fragments[f["id"]]=shape(f["geometry"]); fragment_hashes[f["id"]]=fragment_digest(f)
 if len(fragments)!=2: raise ValueError("expected exactly two complete fragments")
 receipts=[]; counts={fid:{} for fid in fragments}
 execution=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
 baseline="0f08ca8c451e71bb3b06cb5fb82988e92d3048ab"
 if subprocess.call(["git","merge-base","--is-ancestor",baseline,execution],cwd=ROOT)!=0:
  raise ValueError("fresh main baseline is not an ancestor of execution commit")
 if subprocess.check_output(["git","status","--porcelain","--untracked-files=no"],cwd=ROOT,text=True).strip():
  raise ValueError("tracked changes present during source sampling")
 transformer=Transformer.from_crs("EPSG:4326","EPSG:4326",always_xy=True)
 for tile in TILES:
  url=BASE.format(tile); local=CACHE/(tile+"_Map.tif")
  request=urllib.request.Request(url,method="HEAD",headers={"User-Agent":"WorldAtlas-geography-20261006/1.0"})
  with urllib.request.urlopen(request,timeout=60) as response:
   head={k.lower():v for k,v in response.headers.items()}
  if not local.exists() or local.stat().st_size!=int(head["content-length"]):
   req=urllib.request.Request(url,headers={"User-Agent":"WorldAtlas-geography-20261006/1.0"})
   with urllib.request.urlopen(req,timeout=180) as response,open(local,"wb") as out:
    while True:
     block=response.read(8*1024*1024)
     if not block: break
     out.write(block)
  actual_sha=sha(local)
  if (local.stat().st_size,actual_sha,head.get("etag")) != EXPECTED[tile]:
   raise ValueError(f"WorldCover source object identity mismatch for {tile}: size/hash/ETag differ")
  tile_record={"tile":tile,"url":url,"retrieved_date_utc":time.strftime("%Y-%m-%d",time.gmtime()),
    "bytes":local.stat().st_size,"sha256":actual_sha,"etag":head.get("etag"),"last_modified":head.get("last-modified"),
    "content_type":head.get("content-type"),"retention":"full tile is reproducibly downloadable from the cited public ESA WorldCover v200 S3 URL; kept in ignored local evidence cache because each original COG exceeds the 32 MiB retained-file bound"}
  with rasterio.open(local) as ds:
   tile_record.update({"crs":str(ds.crs),"bounds":[ds.bounds.left,ds.bounds.bottom,ds.bounds.right,ds.bounds.top],
                       "width":ds.width,"height":ds.height,"dtype":ds.dtypes[0],"nodata":ds.nodata,"block_shapes":[list(x) for x in ds.block_shapes],"tags":ds.tags()})
   tile_poly=box(ds.bounds.left,ds.bounds.bottom,ds.bounds.right,ds.bounds.top)
   for fid,geom in fragments.items():
    cut=geom.intersection(tile_poly)
    if cut.is_empty or cut.area == 0: continue
    arr,affine=mask(ds,[mapping(cut)],crop=True,all_touched=False,filled=False)
    vals=arr[0].compressed()
    if not len(vals): continue
    unique,n=np.unique(vals,return_counts=True)
    counts[fid][tile]={str(int(k)):int(v) for k,v in zip(unique,n)}
  receipts.append(tile_record)
 labels={10:"tree_cover",20:"shrubland",30:"grassland",40:"cropland",50:"built_up",60:"bare_or_sparse_vegetation",70:"snow_and_ice",80:"permanent_water",90:"herbaceous_wetland",95:"mangroves",100:"moss_and_lichen"}
 summary={}
 for fid,by_tile in counts.items():
  combined={}
  for table in by_tile.values():
   for key,value in table.items(): combined[key]=combined.get(key,0)+value
  total=sum(combined.values())
  summary[fid]={"fragment_feature_sha256":fragment_hashes[fid],"pixel_count":total,"class_pixel_counts":combined,"class_labels":{k:labels.get(int(k),"unknown class") for k in combined},
                "water_class_80_pixel_count":combined.get("80",0),"water_class_80_fraction":combined.get("80",0)/total if total else None,
                "tile_pixel_counts":by_tile}
 result={"schema":"geo4-worldcover-seam-window-v1","actual_execution_sha":execution,"baseline_main_sha":baseline,"reproduction_code_sha256":sha(Path(__file__)),"source":{"product":"ESA WorldCover 10 m 2021 v200 map","release_date":RELEASED,
   "doi":"10.5281/zenodo.7254221","license":"CC BY 4.0","official_access":"https://esa-worldcover.org/en/data-access",
   "whole_tile_restoration":"GET the exact public S3 URL recorded for each tile; match byte count, SHA-256, ETag and Last-Modified before rerun.",
   "validation_limit":"ESA reports global overall accuracy 76.7%; land-cover pixels are not legal water status, an administrative boundary, or proof of sovereignty."},
  "retrieval_day_utc":time.strftime("%Y-%m-%d",time.gmtime()),"method":{"software":f"Python/rasterio {rasterio.__version__}; NumPy {np.__version__}; Shapely window-mask; pixel centers selected (all_touched=false)","crs":"EPSG:4326","scope":"all valid 10 m map-class pixels whose centers fall within each exact complete fragment polygon; each intersecting 3x3-degree original COG tile processed independently","water_class_code":80,"no_geometry_edit":True},
  "tiles":receipts,"fragment_summaries":summary,
  "limits":["2021 class map is independently dated relative to geoBoundaries’ 2018, 2019, and 2021 administrative vintages but does not identify a survey date for every pixel.","Land-cover class is an uncertain physical-surface proxy; class 80 supports a water-like classification only at product resolution and accuracy.","No sovereign or administrative affiliation is inferred; no original/current boundary or physical-gap geometry is modified."]}
 (OUT/"worldcover-window-summary.json").write_text(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n")
 print(json.dumps({fid:{"pixel_count":x["pixel_count"],"classes":x["class_pixel_counts"],"water80_fraction":x["water_class_80_fraction"]} for fid,x in summary.items()},indent=2))
 print("saved",OUT/"worldcover-window-summary.json")
if __name__=="__main__": main()
