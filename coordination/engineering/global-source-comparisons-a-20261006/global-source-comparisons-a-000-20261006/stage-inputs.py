"""Retain exact original inputs and first-run provenance; no geometry operations."""
import pathlib, json, gzip, hashlib, subprocess, argparse

def canon(value):
    return (json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)+"\n").encode()
def digest(body): return hashlib.sha256(body).hexdigest()
p=argparse.ArgumentParser();p.add_argument("--repo",required=True);p.add_argument("--historical-root",required=True);args=p.parse_args()
repo=pathlib.Path(args.repo);root=pathlib.Path(__file__).parent;old=pathlib.Path(args.historical_root)
scope=json.loads((root/"scope.json").read_bytes());selected=set(scope["complete_component_ids"]);source_ids=set(scope["source_ids"])
def git(commit,path):
    mode=subprocess.check_output(["git","-C",str(repo),"ls-tree",commit,"--",path]).split()[0]
    assert mode in (b"100644",b"100755")
    return subprocess.check_output(["git","-C",str(repo),"show",commit+":"+path])
inputs=root/"inputs";inputs.mkdir(exist_ok=True);aliases=[];written={}
for pin in scope["full_input_pins"]:
    commit=pin.get("commit","1c4b606d35614bd7c4990bb9da1098fa181c7fe8")
    body=git(commit,pin["path"]);assert len(body)==pin["bytes"] and digest(body)==pin["sha256"]
    raw=gzip.decompress(body) if body[:2]==b"\x1f\x8b" else body
    assert max(len(body),len(raw))<=32*1024*1024
    if "uncompressed_sha256" in pin:
        assert digest(raw)==pin["uncompressed_sha256"] and len(raw)==pin["uncompressed_bytes"]
    name=pin["sha256"]+".bin"
    if name not in written:
        destination=inputs/name
        if destination.exists():assert destination.read_bytes()==body
        else:destination.write_bytes(body)
        written[name]=len(body)
    aliases.append({"original_commit":commit,"original_path":pin["path"],"owned_path":"inputs/"+name,"original_pin":pin})
(root/"input-aliases.json").write_bytes(canon({"aliases":aliases,"encoded_unique_bytes":sum(written.values())}))
expected=[];sources={};receipts=[]
cohorts=["initial251","additive-admin-partition-0","additive-admin-partition-1","additive-india-refinement","next-administrative-single-edge","next-administrative-zero-edge","next-distinct-India-refinement-single-edge","next-distinct-India-refinement-zero-edge"]
def checked(pin):
    path=pathlib.Path(pin["path"]);path=path if path.is_absolute() else old.parents[2]/path;body=path.read_bytes();assert len(body)==pin["bytes"] and digest(body)==pin["sha256"]
    raw=gzip.decompress(body);assert len(raw)==pin["decoded_bytes"] and digest(raw)==pin["decoded_sha256"]
    return json.loads(raw)
for name in cohorts:
    folder=old if name=="initial251" else old/name
    raw=(folder/"receipt.json").read_bytes();receipt=json.loads(raw)
    receipts.append({"cohort":name,"original_private_producer_sha256":receipt["script_sha256"],"actual_scientific_executions":1,"raw_receipt_bytes":len(raw),"raw_receipt_sha256":digest(raw),"retained_receipt":"historical/"+name+"-receipt.json.gz"})
    (root/"historical"/(name+"-receipt.json.gz")).write_bytes(gzip.compress(raw,mtime=0))
    for row in json.loads((folder/"complete-source-inputs.json").read_bytes())["source_products"]:
        if row["source_id"] in source_ids:sources.setdefault(row["source_id"],row)
    for pin in receipt["outputs"]:
        for ordinal,row in enumerate(checked(pin)):
            if row["component"] in selected:
                expected.append({"component":row["component"],"family":row["family"],"cohort":name,"original_file":pin,"ordinal":ordinal,"canonical_original_row_sha256":digest(canon(row))})
    print("authenticated old cohort",name,flush=True)
assert len(expected)==len(selected) and {row["component"] for row in expected}==selected
assert set(sources)==source_ids
(root/"historical-original-rows.json.gz").write_bytes(gzip.compress(canon(expected),mtime=0))
(root/"historical-source-bindings.json.gz").write_bytes(gzip.compress(canon(sources),mtime=0))
(root/"historical-executions.json").write_bytes(canon(receipts))
remaining=(old/"complete-remaining-6023-family-original-member-closure-plan.json").read_bytes()
assert digest(remaining)=="c1fbd02007b403e064b5ac02e2eea4a06652c1ae56a78aef33cc7a375d25e990"
(root/"remaining-complete-source-member-plan.json.gz").write_bytes(gzip.compress(remaining,mtime=0))
print("PASS exact input custody; no science execution",len(selected),len(aliases),sum(written.values()),flush=True)
