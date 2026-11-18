import test from "node:test";
import assert from "node:assert/strict";
import worker from "../worker.js";

const request = (path, method = "GET") =>
  new Request(`https://atlas.example${path}`, { method });
const env = { ATLAS: { get: async () => null } };

test("health reports service readiness", async () => {
  const result = await worker.fetch(request("/health"), env);
  assert.equal(result.status, 200);
  assert.deepEqual(await result.json(), { project: "worldatlas", status: "ready" });
  const head = await worker.fetch(request("/health", "HEAD"), env);
  assert.equal(head.headers.get("Content-Type"), "application/json");
  assert.equal(head.body, null);
});

test("evidence and arbitrary bucket paths are not publicly routed", async () => {
  for (const path of [
    "/sources/source.zip",
    "/private",
    "/review/../evidence/source.zip",
    "/review/%2fsecret",
  ]) {
    assert.equal((await worker.fetch(request(path), env)).status, 404);
  }
});

test("release routes are read-only", async () => {
  assert.equal(
    (await worker.fetch(request("/releases/v9.0-rc.1/index.html", "POST"), env)).status,
    405,
  );
});

test("missing index is explicitly unfinished", async () => {
  assert.match(
    await (await worker.fetch(request("/"), env)).text(),
    /no published map yet/,
  );
});

test("release assets keep their stored media type and support HEAD", async () => {
  const seen = [];
  const bound = {
    ATLAS: {
      get: async () => { throw Error("HEAD must use bucket metadata"); },
      head: async (key) => {
        seen.push(key);
        return {
          httpEtag: '"abc"',
          writeHttpMetadata: (h) => h.set("Content-Type", "application/gzip"),
        };
      },
    },
  };
  const response = await worker.fetch(
    request("/releases/v9.0-rc.1/rows.u32le.gz", "HEAD"),
    bound,
  );
  assert.deepEqual(seen, ["releases/v9.0-rc.1/rows.u32le.gz"]);
  assert.equal(response.headers.get("Content-Type"), "application/gzip");
  assert.equal(response.headers.get("Content-Encoding"), null);
  assert.equal(await response.text(), "");
});

test("numbered candidates stay separate from the published homepage", async () => {
  const requested = [];
  function read(key) {
    requested.push(key);
    if (key === "index.html") return { body: "V8" };
    if (key === "releases/v9.0-rc.1/index.html" || key === "releases/v9.0-rc.2/index.html") {
      return { body: key.includes("rc.1") ? "First candidate" : "Second candidate",
        httpEtag: '"candidate"', writeHttpMetadata: h => h.set("Content-Type", "text/html") };
    }
    return null;
  }
  const storage = { ATLAS: { get: read, head: read } };
  assert.equal(await (await worker.fetch(request("/"), storage)).text(), "V8");
  assert.equal((await worker.fetch(request("/", "HEAD"), storage)).body, null);
  assert.equal(await (await worker.fetch(request("/releases/v9.0-rc.1/index.html"), storage)).text(), "First candidate");
  assert.equal(await (await worker.fetch(request("/releases/v9.0-rc.2/index.html"), storage)).text(), "Second candidate");
  assert.equal(await (await worker.fetch(request("/releases/v9.0-rc.1/index.html", "HEAD"), storage)).text(), "");
  assert.equal((await worker.fetch(request("/v9.0-rc"), storage)).status, 404);
  assert.equal((await worker.fetch(request("/releases/v9.0-rc.3/index.html"), storage)).status, 404);
  assert.deepEqual(requested, [
    "index.html",
    "index.html",
    "releases/v9.0-rc.1/index.html",
    "releases/v9.0-rc.2/index.html",
    "releases/v9.0-rc.1/index.html",
    "releases/v9.0-rc.3/index.html",
  ]);
});

test("retired review and version shortcuts are not routed", async () => {
  for (const path of ["/review/index.html", "/review/releases/v8.2-rc.5/index.html",
                      "/review/v8.0/sources.html", "/v8.0/sources", "/v8.0/sources.html"])
    assert.equal((await worker.fetch(request(path), env)).status, 404);
});
