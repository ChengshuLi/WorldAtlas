import { gunzipSync } from "node:zlib";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { createHash } from "node:crypto";
export const ROOT = path.dirname(fileURLToPath(import.meta.url));
const sha = (b) => createHash("sha256").update(b).digest("hex");
// Pure extraction consumes the authenticated immutable reader supplied by its caller.
function intervalReader(load) {
  const sourcePins = JSON.parse(load("source-census-summary.json")).blocks;
  const physicalPins = JSON.parse(load("physical-unassigned-summary.json")).phases;
  const pinFor = (prefix, b) => {
    const pin =
      prefix === "source-candidates"
        ? sourcePins[b]
        : physicalPins[b].files.find((f) => f.kind === prefix);
    if (!pin) throw Error("Missing interval pin");
    return pin;
  };
  const members = (prefix, b) => {
    const pin = pinFor(prefix, b);
    return pin.parts ?? [{...pin, path: prefix + "-block-" + String(b).padStart(3, "0") + ".json.gz"}];
  };
  const read = (prefix, b) => {
    const pin = pinFor(prefix, b);
    if (pin.parts) {
      const rows = [];
      for (const part of pin.parts) {
        const compressed = load(part.path);
        if (sha(compressed) !== part.sha256)
          throw Error("Encoded interval part hash mismatch");
        const decoded = gunzipSync(compressed);
        if (sha(decoded) !== part.decoded_sha256)
          throw Error("Decoded interval part hash mismatch");
        rows.push(...JSON.parse(decoded));
      }
      if (sha(JSON.stringify(rows) + "\n") !== pin.decoded_sha256)
        throw Error("Complete split interval hash mismatch");
      return rows;
    }
    const raw = load(members(prefix, b)[0].path);
    if (sha(raw) !== pin.sha256) throw Error("Encoded interval hash mismatch");
    const decoded = gunzipSync(raw);
    if (sha(decoded) !== pin.decoded_sha256)
      throw Error("Decoded interval hash mismatch");
    return JSON.parse(decoded);
  };
  return {read, inputs: blocks => blocks.flatMap(b =>
    ["source-candidates", "physical-support", "inland-water-support"].flatMap(prefix => members(prefix, b)))};
}
export function context(load) {
  return {
    features: JSON.parse(load("source-feature-roster.json")),
    raster: JSON.parse(load("source-raster-summary.json")),
  };
}
function hits(a, z, rs) {
  let l = 0,
    h = rs.length;
  while (l < h) {
    const m = (l + h) >> 1;
    if (rs[m][1] <= a) l = m + 1;
    else h = m;
  }
  const out = [];
  for (let j = l; j < rs.length && rs[j][0] < z; j++) {
    const p = Math.max(a, rs[j][0]),
      q = Math.min(z, rs[j][1]);
    if (p < q) out.push([p, q]);
  }
  return out;
}
export function* segments(b, ctx, readIntervals) {
  const rows = readIntervals("source-candidates", b),
    land = new Map(readIntervals("physical-support", b).map((r) => [r.y, r.runs])),
    water = new Map(readIntervals("inland-water-support", b).map((r) => [r.y, r.runs]));
  for (const row of rows)
    for (const [a, z, owners, sids] of row.runs) {
      const mapped = sids.filter((s) => ctx.features[s - 1].owners.length);
      let conflict = false;
      if (mapped.length > 1) {
        let common = new Set(ctx.features[mapped[0] - 1].owners);
        for (const s of mapped.slice(1))
          common = new Set(
            ctx.features[s - 1].owners.filter((o) => common.has(o)),
          );
        conflict = common.size === 0;
      }
      const families = [
          ...new Set(
            (mapped.length ? mapped : sids).map(
              (s) => ctx.features[s - 1].family_index,
            ),
          ),
        ].sort((i, j) => {
          if (!mapped.length) {
            const ai = Number(ctx.raster.products[i].product.split("ADM")[1]),
              aj = Number(ctx.raster.products[j].product.split("ADM")[1]);
            if (ai !== aj) return aj - ai;
          }
          return i - j;
        }),
        family = families[0],
        base = !owners.length
          ? "location-mapping"
          : owners.length > 1
            ? conflict
              ? "source-conflict"
              : "shared-lineage"
            : "unique";
      const events = [
        [a, 0, 0],
        [z, 0, 0],
      ];
      for (const [p, q] of hits(a, z, land.get(row.y) ?? []))
        events.push([p, 1, 1], [q, 1, -1]);
      for (const [p, q] of hits(a, z, water.get(row.y) ?? []))
        events.push([p, 2, 1], [q, 2, -1]);
      events.sort((a, b) => a[0] - b[0]);
      let x = a,
        ls = 0,
        ws = 0,
        i = 0;
      while (i < events.length) {
        const stop = events[i][0];
        if (stop > x) {
          const physical = ls
              ? "land"
              : ws
                ? "inland-water"
                : "source-relative",
            category =
              base === "unique"
                ? ls || ws
                  ? "repair-evaluation"
                  : "physical-interpretation"
                : base;
          yield {
            package_id:
              ctx.raster.products[family].product.replaceAll(":", "-") +
              "--" +
              category,
            family,
            category,
            y: row.y,
            start: x,
            end: stop,
            physical,
            owners,
            sids,
          };
        }
        while (i < events.length && events[i][0] === stop) {
          const [, k, d] = events[i++];
          if (k === 1) ls += d;
          if (k === 2) ws += d;
        }
        if (ls && ws) throw Error("Overlapping land/water");
        x = stop;
      }
    }
}
// Derive the complete original package, never a caller-selected witness subset.
// load returns logical metadata bodies and encoded .gz interval members.
export function packageInputs(packageId, load) {
  const manifest = JSON.parse(load("source-package-queue.json"));
  const matches = manifest.packages.filter(p => p.package_id === packageId);
  if (matches.length !== 1) throw Error("Unknown or duplicate package");
  const pkg = matches[0];
  for (const [name, digest] of Object.entries(manifest.input_sha256 ?? {}))
    if (sha(load(name)) !== digest) throw Error("Shared input hash mismatch: " + name);
  const intervals = intervalReader(load);
  return {package: pkg, inputs: intervals.inputs(pkg.native_blocks), readIntervals: intervals.read};
}
export function packageIntervals(packageId, load) {
  const {package: pkg, readIntervals} = packageInputs(packageId, load);
  const ctx = context(load), blocks = [];
  let cells = 0;
  for (const b of pkg.native_blocks) {
    const rows = [];
    for (const s of segments(b, ctx, readIntervals)) if (s.package_id === packageId) {
      rows.push([s.y, s.start, s.end, s.owners, s.sids, s.physical]);
      cells += s.end - s.start;
    }
    blocks.push({block: b, rows});
  }
  if (cells !== pkg.native_cells) throw Error("Batch extraction census mismatch");
  return {package: pkg, blocks, cells};
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url))
  throw Error("Standalone extraction was removed; use scripts/observe-selected-owners.mjs with an exact data commit and package. Its original_intervals contains the complete original table.");
