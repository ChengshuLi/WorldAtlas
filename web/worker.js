// Adapt the Worker's native R2 binding to the data the routes need.
async function readAsset(bucket, key, { head, etag, includeMetadata = false }) {
  const options = etag ? { onlyIf: new Headers({ "If-None-Match": etag }) } : undefined;
  const object = await (head ? bucket.head(key) : bucket.get(key, options));
  if (!object) return null;
  const headers = includeMetadata ? new Headers() : null;
  if (headers) {
    object.writeHttpMetadata(headers);
    headers.set("ETag", object.httpEtag);
  }
  return {
    body: head ? null : object.body,
    notModified: !head && !("body" in object),
    headers,
  };
}

// Serve release files only. Raw sources remain private.
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const head = request.method === "HEAD";
    if (!["GET", "HEAD"].includes(request.method)) {
      return new Response("Method not allowed", {
        status: 405,
        headers: { Allow: "GET, HEAD" },
      });
    }
    if (url.pathname === "/health") {
      if (head) {
        return new Response(null, { headers: { "Content-Type": "application/json" } });
      }
      return Response.json({
        project: "worldatlas",
        status: "ready",
      });
    }
    if (["/", "/index.html"].includes(url.pathname)) {
      const index = await readAsset(env.ATLAS, "index.html", { head });
      if (!index) {
        return new Response(
          head ? null : "WorldAtlas has no published map yet.",
          {
            headers: {
              "Content-Type": "text/plain; charset=utf-8",
              "Cache-Control": "no-store",
            },
          },
        );
      }
      return new Response(index.body, {
        headers: {
          "Content-Type": "text/html; charset=utf-8",
          "Cache-Control": "no-cache",
        },
      });
    }
    const key = url.pathname.slice(1);
    if (!/^releases\/v[0-9]+\.[0-9]+(?:-rc\.[1-9][0-9]*)?\/[A-Za-z0-9_.\/-]+$/.test(key)
        || key.split("/").some(part => part === "." || part === "..")) {
      return new Response(head ? null : "Not found", { status: 404 });
    }
    const etag = request.headers.get("If-None-Match");
    const asset = await readAsset(env.ATLAS, key, { head, etag, includeMetadata: true });
    if (!asset) return new Response("Not found", { status: 404 });
    asset.headers.set("X-Content-Type-Options", "nosniff");
    asset.headers.set("Cache-Control", "public, max-age=300");
    return new Response(asset.body, {
      status: asset.notModified ? 304 : 200,
      headers: asset.headers,
    });
  },
};
