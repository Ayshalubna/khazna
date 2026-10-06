/* Khazna in the browser.
 *
 * Used only by the static build (scripts/build_static.py). It loads Python (Pyodide) and the same Khazna engine
 * into this page, then answers the web app's /api/* requests locally instead of over the network. Documents,
 * questions and uploaded files never leave the visitor's device.
 */
(function () {
  "use strict";
  const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/";
  const realFetch = window.fetch.bind(window);
  let py = null;            // khazna.browser module
  let outbound = 0;         // requests to other hosts after start-up
  let bootedAt = null;

  function status(msg) {
    const el = document.querySelector("#main .loading");
    if (el) el.textContent = msg;
  }
  const L = () => (document.documentElement.lang === "ar" || (function () { try { return localStorage.getItem("kh_lang") === "ar"; } catch (e) { return false; } })());
  const MSG = {
    py: ["Loading Python into your browser (one time, about 20 MB)…", "جارٍ تحميل بايثون في متصفحك (مرة واحدة، نحو 20 ميغابايت)…"],
    pkgs: ["Loading the search libraries…", "جارٍ تحميل مكتبات البحث…"],
    idx: ["Indexing 21 documents inside your browser…", "جارٍ فهرسة 21 مستندًا داخل متصفحك…"],
    fail: ["Khazna could not start in this browser. Try a recent Chrome, Edge, Firefox or Safari.", "تعذر تشغيل «خزنة» في هذا المتصفح. جرّب إصدارًا حديثًا من Chrome أو Edge أو Firefox أو Safari."],
  };
  const say = (k) => status(MSG[k][L() ? 1 : 0]);

  function loadScript(src) {
    return new Promise((res, rej) => {
      const s = document.createElement("script");
      s.src = src; s.onload = res; s.onerror = () => rej(new Error("script " + src));
      document.head.appendChild(s);
    });
  }

  const ready = (async () => {
    say("py");
    await loadScript(PYODIDE + "pyodide.js");
    const pyodide = await window.loadPyodide({ indexURL: PYODIDE });
    say("pkgs");
    await pyodide.loadPackage(["numpy", "scipy", "scikit-learn", "sqlite3", "micropip"]);
    try {
      const micropip = pyodide.pyimport("micropip");
      await micropip.install("pypdf");                 // PDF uploads; loaded now so nothing is fetched later
    } catch (e) { console.warn("pypdf unavailable; PDF uploads disabled", e); }
    say("idx");
    const zip = await (await realFetch("khazna.zip", { cache: "no-cache" })).arrayBuffer();
    pyodide.unpackArchive(zip, "zip", { extractDir: "/app" });
    pyodide.runPython("import sys; sys.path.insert(0, '/app')");
    py = pyodide.pyimport("khazna.browser");
    py.boot();
    bootedAt = performance.now();
    // From here on, count every request this page makes to another host.
    try {
      new PerformanceObserver((list) => {
        for (const e of list.getEntries()) {
          try { if (new URL(e.name).origin !== location.origin) outbound += 1; } catch (x) { /* ignore */ }
        }
      }).observe({ type: "resource", buffered: false });
    } catch (e) { /* older browsers */ }
    return pyodide;
  })();
  ready.catch((e) => { console.error(e); say("fail"); });

  // ------------------------------------------------------------------ the local "server"
  const json = (status, body) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
  const call = (name, args) => JSON.parse(py.call(name, JSON.stringify(args)));
  const patchEgress = (b) => { if (b && b.egress) b.egress.blocked_attempts = outbound; return b; };

  function sse(result) {
    const enc = new TextEncoder();
    return new Response(new ReadableStream({
      start(ctrl) {
        if (result.status === 200) {
          const b = result.body;
          ctrl.enqueue(enc.encode(`data: ${JSON.stringify({ type: "sources", sources: b.sources.map((s) => ({ n: s.n, title: s.title, section: s.section })) })}\n\n`));
          ctrl.enqueue(enc.encode(`data: ${JSON.stringify(Object.assign({ type: "final" }, b))}\n\n`));
        }
        ctrl.close();
      },
    }), { status: result.status, headers: { "Content-Type": "text/event-stream" } });
  }

  async function route(url, init) {
    await ready;
    const method = (init.method || "GET").toUpperCase();
    const headers = new Headers(init.headers || {});
    const sid = headers.get("X-Khazna-Session") || "";
    const q = url.searchParams;
    const p = url.pathname;
    const body = () => { try { return JSON.parse(init.body || "{}"); } catch (e) { return {}; } };
    let m;
    if (p === "/health") { const r = call("health", {}); return json(r.status, r.body); }
    if (p === "/api/meta") { const r = call("meta", {}); return json(r.status, patchEgress(r.body)); }
    if (p === "/api/library") { const r = call("library", { role: q.get("role"), sid }); return json(r.status, r.body); }
    if ((m = p.match(/^\/api\/documents\/([^/]+)$/))) {
      const r = call("document", { id: decodeURIComponent(m[1]), role: q.get("role"), sid }); return json(r.status, r.body);
    }
    if (p === "/api/ask" && method === "POST") { const r = call("ask", Object.assign(body(), { sid })); return json(r.status, r.body); }
    if (p === "/api/ask/stream" && method === "POST") {
      await new Promise((res) => setTimeout(res, 30));      // let the "searching" state paint before the synchronous work
      return sse(call("ask", Object.assign(body(), { sid })));
    }
    if (p === "/api/scan" && method === "POST") { const r = call("scan", body()); return json(r.status, r.body); }
    if (p === "/api/privacy") { const r = call("privacy", { sid }); return json(r.status, patchEgress(r.body)); }
    if (p === "/api/eval") { const r = call("eval", {}); return json(r.status, r.body); }
    if (p === "/api/upload" && method === "POST") {
      const f = init.body instanceof FormData ? init.body.get("file") : null;
      if (!f) return json(422, { detail: "file required" });
      if (f.size > 5 * 1024 * 1024) return json(422, { detail: "Files must be 5 MB or smaller." });
      const bytes = new Uint8Array(await f.arrayBuffer());
      const r = JSON.parse(py.upload(sid, f.name, bytes));
      return json(r.status, r.body);
    }
    if ((m = p.match(/^\/api\/upload\/([^/]+)$/)) && method === "DELETE") {
      const r = call("delete_upload", { id: decodeURIComponent(m[1]), sid }); return json(r.status, r.body);
    }
    return json(404, { detail: "not found" });
  }

  window.fetch = function (input, init) {
    let url;
    try { url = new URL(typeof input === "string" ? input : input.url, location.href); } catch (e) { return realFetch(input, init); }
    if (url.origin === location.origin && (url.pathname.startsWith("/api/") || url.pathname === "/health")) {
      return route(url, init || {}).catch((e) => { console.error(e); return json(500, { detail: String(e) }); });
    }
    return realFetch(input, init);
  };
  window.KH_RUNTIME = "browser";
})();
