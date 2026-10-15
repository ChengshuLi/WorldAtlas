# Exact worker-merge.yml readback shell at accepted f43770d6b60a7826cd861d2c3954b9db7c886e9d.
if node --input-type=module -e '
  import fs from "node:fs";
  const file="data/ownership-selection.json", stat=fs.lstatSync(file);
  if (!stat.isFile() || stat.isSymbolicLink() || stat.size>33554432) throw Error("Nonordinary selection");
  const s=JSON.parse(fs.readFileSync(file,"utf8"));
  const safe=p=>typeof p==="string" && p.length>0 && !p.startsWith("/") && !p.includes("\\") && p.split("/").every(x=>x!=="" && x!=="." && x!=="..");
  const hash=v=>typeof v==="string" && /^[a-f0-9]{64}$/.test(v);
  if (s?.version!==1 || s.method!=="native-linear-evenodd-first-owner-v1" || !safe(s.manifest_path) || !hash(s.sha256) || typeof s.release_id!=="string" || !s.release_id) throw Error("Malformed native selection");
  if (!Object.hasOwn(s,"artifact_consumption")) process.exit(3);
  const a=s.artifact_consumption;
  if (!a || typeof a!=="object" || Object.keys(a).sort().join(",")!=="certificate,review") throw Error("Malformed artifact selection");
  for (const p of [a.certificate,a.review]) if (!p || !safe(p.path) || p.mode!=="100644" || !Number.isSafeInteger(p.bytes) || p.bytes<=0 || p.bytes>33554432 || !hash(p.sha256)) throw Error("Malformed artifact pin");
'; then
  test -f coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/model-reader-call-boundary-controls.mjs || { echo 'Selected artifact readback helper is missing.' >&2; exit 1; }
  node coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/model-reader-call-boundary-controls.mjs --built-output-readback .cache/native-normal-built-output.json
else
  status=$?
  if test "$status" -ne 3; then exit "$status"; fi
  echo 'No artifact selection: native built-output readback is inapplicable; no report claimed.'
fi
