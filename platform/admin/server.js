const http = require("node:http");
const { createReadStream, statSync } = require("node:fs");
const { extname, join, normalize } = require("node:path");

const root = __dirname;
const port = Number(process.env.PORT || 5174);
const apiBaseUrl = (process.env.PLANTLAB_ADMIN_API_BASE_URL || process.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
};

const server = http.createServer((request, response) => {
  const url = new URL(request.url || "/", "http://localhost");
  if (url.pathname === "/config.js") {
    response.writeHead(200, {
      "content-type": "text/javascript; charset=utf-8",
      "cache-control": "no-store",
    });
    response.end(`window.PLANTLAB_ADMIN_CONFIG = ${JSON.stringify({ apiBaseUrl })};`);
    return;
  }

  const safePath = normalize(decodeURIComponent(url.pathname)).replace(/^(\.\.[/\\])+/, "").replace(/^[/\\]+/, "");
  const filePath = join(root, safePath === "" ? "index.html" : safePath);
  try {
    const stat = statSync(filePath);
    if (!stat.isFile()) {
      throw new Error("Not a file");
    }
    response.writeHead(200, { "content-type": contentTypes[extname(filePath)] || "application/octet-stream" });
    createReadStream(filePath).pipe(response);
  } catch {
    response.writeHead(200, { "content-type": "text/html; charset=utf-8" });
    createReadStream(join(root, "index.html")).pipe(response);
  }
});

server.listen(port, "0.0.0.0", () => {
  console.log(`[admin] listening on http://0.0.0.0:${port}`);
  console.log(`[admin] API base URL: ${apiBaseUrl}`);
});
