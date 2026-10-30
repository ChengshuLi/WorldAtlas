import test from "node:test";
import assert from "node:assert/strict";
import worker from "../web/worker.js";

const request = (path, method = "GET") =>
  new Request(`https://atlas.example${path}`, { method });
const env = { ATLAS: { get: async () => null } };

test("health does not claim geography approval", async () => {
  const result = await worker.fetch(request("/health"), env);
  assert.equal(result.status, 200);
  assert.equal((await result.json()).geography, "not_approved");
});

test("evidence and arbitrary bucket paths are not publicly routed", async () => {
  for (const path of [
    "/evidence/source.zip",
    "/private",
    "/review/../evidence/source.zip",
    "/review/%2fsecret",
  ]) {
    assert.equal((await worker.fetch(request(path), env)).status, 404);
  }
});

test("the review surface is read-only", async () => {
  assert.equal(
    (await worker.fetch(request("/review/proposal.json", "POST"), env)).status,
    405,
  );
});

test("missing index is explicitly unfinished", async () => {
  assert.match(
    await (await worker.fetch(request("/"), env)).text(),
    /No partition has been approved/,
  );
});

test("review assets keep their stored media type and support HEAD", async () => {
  const seen = [];
  const bound = {
    ATLAS: {
      get: async (key) => {
        seen.push(key);
        return {
          body: "example",
          httpEtag: '"abc"',
          writeHttpMetadata: (h) => h.set("Content-Type", "application/gzip"),
        };
      },
    },
  };
  const response = await worker.fetch(
    request("/review/version/display-cells.u8.gz", "HEAD"),
    bound,
  );
  assert.deepEqual(seen, ["review/version/display-cells.u8.gz"]);
  assert.equal(response.headers.get("Content-Type"), "application/gzip");
  assert.equal(response.headers.get("Content-Encoding"), null);
  assert.equal(await response.text(), "");
});
