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
    const key = url.pathname.slice(1);
    const rangeHeader = request.headers.get("Range");
    let range;
    if (rangeHeader) {
      const match = /^bytes=(\d+)-(\d+)$/.exec(rangeHeader);
      if (!match) return new Response("Single explicit byte range required", { status: 416 });
      const offset = Number(match[1]), end = Number(match[2]);
      if (!Number.isSafeInteger(offset) || !Number.isSafeInteger(end) || end < offset || end - offset + 1 > 4 * 1024 * 1024)
        return new Response("Invalid byte range", { status: 416 });
      const info = await env.ATLAS.head(key);
      if (!info) return new Response("Not found", { status: 404 });
      if (end >= info.size)
        return new Response("Range outside object", { status: 416, headers: { "Content-Range": `bytes */${info.size}` } });
      range = { offset, length: end - offset + 1 };
    }
    const object = await env.ATLAS.get(key, range ? { range } : undefined);
    if (!object) return new Response("Not found", { status: 404 });
    const headers = new Headers();
    object.writeHttpMetadata(headers);
    headers.set("ETag", object.httpEtag);
    headers.set("X-Content-Type-Options", "nosniff");
    headers.set("Cache-Control", "public, max-age=300");
    headers.set("Accept-Ranges", "bytes");
    if (range) {
      headers.set("Content-Range", `bytes ${range.offset}-${range.offset + range.length - 1}/${object.size}`);
      headers.set("Content-Length", String(range.length));
    }
    return new Response(request.method === "HEAD" ? null : object.body, {
      status: range ? 206 : 200,
      headers,
    });
  },
};
