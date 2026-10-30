// Only deliberately published review assets are exposed. Evidence stays private.
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (!["GET", "HEAD"].includes(request.method)) {
      return new Response("Method not allowed", {
        status: 405,
        headers: { Allow: "GET, HEAD" },
      });
    }
    if (url.pathname === "/health") {
      return Response.json({
        project: "worldatlas",
        status: "ready",
        geography: "not_approved",
      });
    }
    if (url.pathname === "/") {
      const index = await env.ATLAS.get("review/index.html");
      if (!index) {
        return new Response(
          "WorldAtlas: continent cell-map research is in progress. No partition has been approved.",
          {
            headers: {
              "Content-Type": "text/plain; charset=utf-8",
              "Cache-Control": "no-store",
            },
          },
        );
      }
      return new Response(request.method === "HEAD" ? null : index.body, {
        headers: {
          "Content-Type": "text/html; charset=utf-8",
          "Cache-Control": "no-cache",
        },
      });
    }
    if (!url.pathname.startsWith("/review/") || url.pathname.includes("%")) {
      return new Response("Not found", { status: 404 });
    }
    const object = await env.ATLAS.get(url.pathname.slice(1));
    if (!object) return new Response("Not found", { status: 404 });
    const headers = new Headers();
    object.writeHttpMetadata(headers);
    headers.set("ETag", object.httpEtag);
    headers.set("X-Content-Type-Options", "nosniff");
    headers.set("Cache-Control", "public, max-age=300");
    return new Response(request.method === "HEAD" ? null : object.body, {
      headers,
    });
  },
};
