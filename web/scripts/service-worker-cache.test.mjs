import assert from "node:assert/strict";
import { test } from "node:test";
import vm from "node:vm";
import { GET } from "../app/sw.js/route.js";

async function scriptRequestUsesCache(mode) {
  const previousMode = process.env.NODE_ENV;
  let source;
  try {
    process.env.NODE_ENV = mode;
    source = await GET().text();
  } finally {
    if (previousMode === undefined) delete process.env.NODE_ENV;
    else process.env.NODE_ENV = previousMode;
  }

  const handlers = new Map();
  vm.runInNewContext(source, {
    URL,
    self: { addEventListener: (name, handler) => handlers.set(name, handler) },
    caches: { match: async () => "cached script with the old API URL" },
  });
  let intercepted = false;
  let response;
  handlers.get("fetch")({
    request: {
      url: "http://localhost:3000/_next/static/chunks/app.js",
      method: "GET",
      mode: "cors",
      destination: "script",
      headers: new Headers(),
    },
    respondWith: (value) => {
      intercepted = true;
      response = value;
    },
  });
  if (intercepted) await response;
  return intercepted;
}

test("development scripts bypass stale service worker cache", async () => {
  assert.equal(await scriptRequestUsesCache("development"), false);
});

test("production scripts keep the existing cache behavior", async () => {
  assert.equal(await scriptRequestUsesCache("production"), true);
});
