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
    const readAsset = (key, options) => (head ? env.ATLAS.head(key) : env.ATLAS.get(key, options));
    if (["/", "/index.html"].includes(url.pathname)) {
      const index = await readAsset("index.html");
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
      return new Response(head ? null : index.body, {
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
    const options = etag ? { onlyIf: new Headers({ "If-None-Match": etag }) } : undefined;
    const object = await readAsset(key, options);
    if (!object) return new Response(head ? null : "Not found", { status: 404 });
    const headers = new Headers();
    object.writeHttpMetadata(headers);
    headers.set("ETag", object.httpEtag);
    headers.set("X-Content-Type-Options", "nosniff");
    headers.set("Cache-Control", "public, max-age=300");
    // A failed R2 condition returns metadata without the object body.
    if (!head && !("body" in object)) return new Response(null, { status: 304, headers });
    return new Response(head ? null : object.body, { headers });
  },
};
