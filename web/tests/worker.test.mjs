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
    /no published map yet/,
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

test('packed chunks return exact range metadata and forward bounded reads', async () => {
  let options;
  const rangeEnv={ATLAS:{head:async()=>({size:100}),get:async(key,o)=>{
    options=o; return {body:new Uint8Array([1,2,3]),size:100,httpEtag:'"pack"',writeHttpMetadata:h=>h.set('Content-Type','application/octet-stream')};
  }}};
  const result=await worker.fetch(new Request('https://atlas.example/review/test.pack',{headers:{Range:'bytes=10-12'}}),rangeEnv);
  assert.equal(result.status,206);
  assert.equal(result.headers.get('Content-Range'),'bytes 10-12/100');
  assert.deepEqual(options,{range:{offset:10,length:3}});
  assert.deepEqual([...new Uint8Array(await result.arrayBuffer())],[1,2,3]);
});
test('invalid, multi-part and outside ranges are rejected', async () => {
  for(const range of ['bytes=-20','bytes=20-10','bytes=0-1,3-4','bytes=0-99999999','bytes=99-101']){
    const result=await worker.fetch(new Request('https://atlas.example/review/test.pack',{headers:{Range:range}}),{ATLAS:{head:async()=>({size:100}),get:async()=>{throw Error('must not read')}}});
    assert.equal(result.status,416);
  }
});


test("V8 sources aliases expose only the known public source page", async () => {
  const seen = [];
  const bound = { ATLAS: { get: async key => { seen.push(key); return { body: "source page", httpEtag: "\"abc\"", writeHttpMetadata: h => h.set("Content-Type", "text/html") }; } } };
  for (const path of ["/v8.0/sources", "/v8.0/sources.html", "/review/v8.0/sources.html"]) {
    const result = await worker.fetch(request(path), bound);
    assert.equal(result.status, 200);
    assert.equal(await result.text(), "source page");
  }
  assert.deepEqual(seen, ["review/v8.0/sources.html", "review/v8.0/sources.html", "review/v8.0/sources.html"]);
  for (const path of ["/v8.0/private", "/v8.0/sources%2Fsecret"]) assert.equal((await worker.fetch(request(path), env)).status, 404);
  assert.equal((await worker.fetch(request("/v8.0/sources", "POST"), env)).status, 405);
});

test("numbered candidates stay separate from the published homepage", async () => {
  const requested = [];
  const storage = { ATLAS: { get: async (key) => {
    requested.push(key);
    if (key === "review/index.html") return { body: "V8" };
    if (key === "review/releases/v9.0-rc.1/index.html" || key === "review/releases/v9.0-rc.2/index.html") {
      return { body: key.includes("rc.1") ? "First candidate" : "Second candidate",
        httpEtag: '"candidate"', writeHttpMetadata: h => h.set("Content-Type", "text/html") };
    }
    return null;
  } } };
  assert.equal(await (await worker.fetch(request("/"), storage)).text(), "V8");
  assert.equal(await (await worker.fetch(request("/review/releases/v9.0-rc.1/index.html"), storage)).text(), "First candidate");
  assert.equal(await (await worker.fetch(request("/review/releases/v9.0-rc.2/index.html"), storage)).text(), "Second candidate");
  assert.equal(await (await worker.fetch(request("/review/releases/v9.0-rc.1/index.html", "HEAD"), storage)).text(), "");
  assert.equal((await worker.fetch(request("/v9.0-rc"), storage)).status, 404);
  assert.equal((await worker.fetch(request("/review/releases/v9.0-rc.3/index.html"), storage)).status, 404);
  assert.deepEqual(requested, [
    "review/index.html",
    "review/releases/v9.0-rc.1/index.html",
    "review/releases/v9.0-rc.2/index.html",
    "review/releases/v9.0-rc.1/index.html",
    "review/releases/v9.0-rc.3/index.html",
  ]);
});
