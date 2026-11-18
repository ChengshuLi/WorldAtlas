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
    const readAsset = (key) => (head ? env.ATLAS.head(key) : env.ATLAS.get(key));
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
    const object = await readAsset(key);
    if (!object) return new Response(head ? null : "Not found", { status: 404 });
    const headers = new Headers();
    object.writeHttpMetadata(headers);
    headers.set("ETag", object.httpEtag);
    headers.set("X-Content-Type-Options", "nosniff");
    headers.set("Cache-Control", "public, max-age=300");
    return new Response(head ? null : object.body, { headers });
  },
};
