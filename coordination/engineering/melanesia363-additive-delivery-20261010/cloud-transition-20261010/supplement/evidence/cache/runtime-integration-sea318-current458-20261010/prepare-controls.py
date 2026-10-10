from pathlib import Path
r=Path('.cache/runtime-integration-sea318-current458-20261010');s=(r/'caller-proposed318.mjs').read_text()
def cut(a,b):return s[s.index(a):s.index(b,s.index(a))]
text="import {createHash} from 'node:crypto';\nimport {canonicalValue,polygonParts} from '/Users/chengshuli/world-atlas-workspace/.worldatlas-checkout/src/effective-footprint.js';\nconst sha=raw=>createHash('sha256').update(raw).digest('hex');\nconst canonical=value=>Buffer.from(JSON.stringify(canonicalValue(value))+'\\n');\nconst hex=value=>typeof value==='string'&&/^[a-f0-9]{64}$/.test(value);\nfunction demand(value,message){if(!value)throw Error(message);}\n"
foot=Path('.worldatlas-checkout/src/effective-footprint.js').read_text()
text=text.replace("import {canonicalValue,polygonParts} from '/Users/chengshuli/world-atlas-workspace/.worldatlas-checkout/src/effective-footprint.js';\n",foot[foot.index('function require('):foot.index('export function footprintValueSha256')]+foot[foot.index('export function polygonParts'):foot.index('export function effectivePrimitiveGeometries')])
text+=cut('export function wholePrimitivePointsetEqual','export function retainedLandSourcePremises')
text+=cut('export function originalAdministrativeTargetHash','// A separate subgeometry premise.')
text+=cut("const SEA318_BATCH=",'function administrative318SourceScope')
(r/'literal-boundary-controls-module.mjs').write_text(text)
