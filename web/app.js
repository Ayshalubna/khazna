/* Khazna web app: plain JavaScript, no build step, no third-party code. */
(function () {
  "use strict";
  const I18N = window.KH_I18N;
  const $ = (s, el = document) => el.querySelector(s);
  const main = $("#main");

  // ------------------------------------------------------------------ state
  const store = {
    get(k) { try { return window.localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { window.localStorage.setItem(k, v); } catch (e) { /* private mode */ } },
  };
  function newSid() {
    const a = new Uint8Array(12);
    (window.crypto || window.msCrypto).getRandomValues(a);
    return Array.from(a, (b) => b.toString(16).padStart(2, "0")).join("");
  }
  let sid = store.get("kh_sid");
  if (!sid || !/^[A-Za-z0-9]{8,40}$/.test(sid)) { sid = newSid(); store.set("kh_sid", sid); }
  let lang = store.get("kh_lang") === "ar" ? "ar" : "en";
  let role = store.get("kh_role") || "employee";
  let meta = null;
  let lastAnswer = null;      // keep the last answer when switching pages
  const session = { questions: 0, masked: 0, injections: 0 };

  const T = () => I18N[lang];
  /** Text for this runtime: the in-browser build has its own wording for a few strings (key + "_br"). */
  const tx = (key) => { const t = T(); return (meta && meta.runtime === "browser" && t[key + "_br"] !== undefined) ? t[key + "_br"] : t[key]; };

  // ------------------------------------------------------------------ helpers
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const pct = (x) => (x == null ? "–" : `${Math.round(x * 100)}%`);
  const isAr = (s) => /[؀-ۿ]/.test(s || "");
  const KIND_KEY = { "EMIRATES ID": "emirates_id", IBAN: "iban", "CARD NUMBER": "card", PASSPORT: "passport", PHONE: "phone", "E-MAIL": "email", EMAIL: "email" };

  function kindLabel(raw) {
    const k = KIND_KEY[raw] || raw.toLowerCase().replace(/\s+/g, "_");
    return (T().pii_kind[k] || raw);
  }
  /** Escape text, then turn "[EMIRATES ID HIDDEN]" into redaction bars and "[2]" into citation buttons. */
  function richText(text, withCites) {
    let h = esc(text).replace(/\[([A-Z][A-Z \-]{1,20}) HIDDEN\]/g, (_, k) => {
      const lab = esc(kindLabel(k));
      return `<span class="redact" data-kind="${lab}" tabindex="0" role="img" aria-label="${lab}">████████</span>`;
    });
    if (withCites) h = h.replace(/\[(\d{1,2})\]/g, (_, n) => `<button class="cite" type="button" data-n="${n}" aria-label="Source ${n}">${n}</button>`);
    return h;
  }
  function piiSummary(obj) {
    const parts = Object.entries(obj || {}).filter(([, n]) => n > 0).map(([k, n]) => `${n} ${T().pii_kind[k] || k}`);
    return parts.join(", ");
  }
  function toast(msg) {
    const t = $("#toast");
    t.textContent = msg;
    t.classList.add("show");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => t.classList.remove("show"), 3200);
  }
  async function api(path, opts = {}) {
    const headers = Object.assign({ "X-Khazna-Session": sid }, opts.headers || {});
    const r = await fetch(path, Object.assign({}, opts, { headers }));
    if (r.status === 429) { toast(T().rate); throw new Error("rate"); }
    if (!r.ok) {
      let detail = "";
      try { detail = (await r.json()).detail; } catch (e) { /* not json */ }
      const err = new Error(typeof detail === "string" ? detail : `HTTP ${r.status}`);
      err.status = r.status;
      throw err;
    }
    return r.json();
  }
  const roleLabel = (id) => {
    const r = meta && meta.roles.find((x) => x.id === id);
    return r ? (lang === "ar" ? r.label_ar : r.label) : id;
  };
  const roleDocs = (id) => {
    const r = meta && meta.roles.find((x) => x.id === id);
    return r ? r.documents : 0;
  };
  const modelName = () => (meta && meta.model ? meta.model.split("/").pop() : null);

  // ------------------------------------------------------------------ chrome: language, role, menu
  function applyLang() {
    const html = document.documentElement;
    html.lang = lang;
    html.dir = lang === "ar" ? "rtl" : "ltr";
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const v = T()[el.dataset.i18n];
      if (typeof v === "string") el.textContent = v;
    });
    $("#lang").textContent = T().other_lang;
    $("#lang").lang = lang === "ar" ? "en" : "ar";
    document.title = lang === "ar" ? "خزنة — مساعد المستندات الخاص" : "Khazna — private document assistant";
    fillRoles();
  }
  function fillRoles() {
    const sel = $("#role");
    if (!meta) return;
    sel.innerHTML = meta.roles.map((r) => `<option value="${esc(r.id)}">${esc(lang === "ar" ? r.label_ar : r.label)}</option>`).join("");
    if (!meta.roles.some((r) => r.id === role)) role = "employee";
    sel.value = role;
  }
  $("#lang").addEventListener("click", () => {
    lang = lang === "ar" ? "en" : "ar";
    store.set("kh_lang", lang);
    applyLang();
    route();
  });
  $("#role").addEventListener("change", (e) => {
    role = e.target.value;
    store.set("kh_role", role);
    lastAnswer = null;
    route();
  });
  $("#menu").addEventListener("click", () => {
    const m = $("#mnav");
    const open = m.hidden;
    m.hidden = !open;
    $("#menu").setAttribute("aria-expanded", String(open));
  });

  // ------------------------------------------------------------------ router
  const PAGES = { "": pageAsk, library: pageLibrary, upload: pageUpload, evidence: pageEvidence, how: pageHow };
  function route() {
    const name = (location.hash.replace(/^#\/?/, "").split("?")[0]) || "";
    const page = PAGES[name] ? name : "";
    document.querySelectorAll(".nav a, .mnav a").forEach((a) => {
      const target = a.getAttribute("href").replace(/^#\/?/, "");
      if (target === page) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
    });
    $("#mnav").hidden = true;
    $("#menu").setAttribute("aria-expanded", "false");
    closeDrawer();
    PAGES[page]();
  }
  window.addEventListener("hashchange", () => { route(); main.focus({ preventScroll: true }); window.scrollTo(0, 0); });

  // ------------------------------------------------------------------ Ask page
  const EXAMPLES = {
    en: {
      employee: [
        ["What are office working hours during Ramadan?", "version"],
        ["كم يوما إجازة الأمومة؟", "ar"],
        ["What is the nightly hotel limit in Dubai?", ""],
        ["Can I use a USB stick on my work laptop?", ""],
        ["What is the salary band for a G5 manager?", "restricted"],
        ["Does the company pay for cryptocurrency losses?", "off"],
      ],
      hr: [
        ["What is the salary band for a G3 coordinator?", ""],
        ["What is Fatima Al Hammadi's Emirates ID?", "pii"],
        ["كم مدة فترة التجربة للموظف الجديد؟", "cross"],
        ["What was revenue in the first half of 2026?", "restricted"],
      ],
      finance: [
        ["Summarise the SwiftPack proposal.", "injection"],
        ["What is the monthly fixed fee in the Gulf Retail agreement?", ""],
        ["How many quotes are needed for a purchase of AED 50,000?", ""],
        ["Which company are we planning to acquire?", "restricted"],
      ],
      legal: [
        ["Which courts handle disputes under the Gulf Retail contract?", ""],
        ["Within how many days must Gulf Retail pay our invoices?", ""],
        ["What is the housing allowance percentage?", "restricted"],
      ],
      it: [
        ["What number do I call to report a security incident?", ""],
        ["ما الحد الأدنى لطول كلمة المرور؟", "cross"],
        ["What is the bonus target for G7 and G8?", "restricted"],
      ],
      executive: [
        ["Who is the new Chief Financial Officer?", ""],
        ["What does the SwiftPack note say we should do?", "injection"],
        ["What is Fatima Al Hammadi's mobile number?", "pii"],
        ["What is the budget for the new KEZAD warehouse?", ""],
      ],
    },
  };
  EXAMPLES.ar = {
    employee: [
      ["ما هي ساعات العمل في رمضان؟", "version"],
      ["كم يوما إجازة الأمومة؟", ""],
      ["What is the nightly hotel limit in Dubai?", "cross"],
      ["ما هو سلم رواتب المدير؟", "restricted"],
      ["هل تعوض الشركة خسائر العملات الرقمية؟", "off"],
    ],
  };
  ["hr", "finance", "legal", "it", "executive"].forEach((r) => { EXAMPLES.ar[r] = EXAMPLES.en[r]; });

  function pageAsk() {
    const t = T();
    const ex = (EXAMPLES[lang][role] || EXAMPLES.en.employee);
    main.innerHTML = `
<div class="wrap">
  <section class="intro">
    <div>
      <h1>${esc(t.title)}</h1>
      <p class="lede">${esc(tx("lede"))}</p>
    </div>
    <figure class="specimen" aria-label="${esc(t.specimen_title)}">
      <span class="stamp">${esc(t.specimen_stamp)}</span>
      <h3>${esc(t.specimen_title)}</h3>
      <p>${esc(t.specimen_l1)}</p>
      <p>${esc(t.specimen_l2)}: <span class="redact" data-kind="${esc(t.pii_kind.emirates_id)}">784-1990-1234567-1</span></p>
      <p>${esc(t.specimen_l3)}: <span class="redact" data-kind="${esc(t.pii_kind.iban)}">AE07 0331 2345 6789 0123 456</span></p>
      <p>${esc(t.specimen_l4)}: <span class="redact" data-kind="${esc(t.pii_kind.phone)}">+971 50 765 4321</span></p>
    </figure>
  </section>
  <div class="ask-layout">
    <div>
      <form class="askbox" id="askform" autocomplete="off">
        <input id="q" name="q" maxlength="400" required minlength="2" placeholder="${esc(t.ask_ph)}" aria-label="${esc(t.your_q)}">
        <button type="submit" id="askbtn">${esc(t.ask_btn)}</button>
      </form>
      <p class="viewing">${t.viewing(esc(roleLabel(role)), roleDocs(role))}</p>
      <div class="chips" aria-label="${esc(t.try)}">
        ${ex.map(([q, tag]) => `<button type="button" class="chip" data-q="${esc(q)}" ${isAr(q) ? 'dir="rtl" lang="ar"' : 'dir="ltr" lang="en"'}>${tag ? `<span class="tag">${esc(t.tag[tag])}</span>` : ""}${esc(q)}</button>`).join("")}
      </div>
      <div id="out" aria-live="polite"></div>
    </div>
    <aside class="rail">
      <div class="card">
        <h2>${esc(t.rail_h)}</h2>
        <ul class="ledger" id="ledger"></ul>
        <p class="whereis" id="whereis"></p>
      </div>
    </aside>
  </div>
</div>`;
    $("#askform").addEventListener("submit", (e) => { e.preventDefault(); ask($("#q").value); });
    main.querySelectorAll(".chip").forEach((c) => c.addEventListener("click", () => { $("#q").value = c.dataset.q; ask(c.dataset.q); }));
    renderLedger();
    refreshPrivacy();
    if (lastAnswer && lastAnswer.role === role) { $("#q").value = lastAnswer.question; renderAnswer(lastAnswer); }
  }

  function renderLedger(egress) {
    const t = T();
    const el = $("#ledger");
    if (!el) return;
    const g = egress || (meta && meta.egress) || { enabled: false, blocked_attempts: 0 };
    el.innerHTML = `
      <li><span>${esc(t.rail_q)}</span><b>${session.questions}</b></li>
      <li><span>${esc(t.rail_mask)}</span><b class="${session.masked ? "good" : ""}">${session.masked}</b></li>
      <li><span>${esc(t.rail_inj)}</span><b class="${session.injections ? "good" : ""}">${session.injections}</b></li>
      <li><span>${esc(tx("rail_net"))}</span><b>${g.blocked_attempts || 0}</b></li>
      <li><span>${esc(g.enabled ? tx("rail_guard_on") : t.rail_guard_off)}</span><b class="${g.enabled ? "good" : "bad"}">${g.enabled ? "●" : "○"}</b></li>`;
    $("#whereis").textContent = tx("rail_where")(modelName());
  }
  async function refreshPrivacy() {
    try {
      const p = await api("/api/privacy");
      if (meta) meta.egress = p.egress;
      renderLedger(p.egress);
    } catch (e) { /* ledger is optional */ }
  }

  let asking = false;
  async function ask(q) {
    q = (q || "").trim();
    if (q.length < 2 || asking) return;
    asking = true;
    const t = T();
    const btn = $("#askbtn");
    if (btn) btn.disabled = true;
    const out = $("#out");
    const qdir = isAr(q) ? "rtl" : "ltr";
    out.innerHTML = `<article class="answer"><p class="q" dir="${qdir}">${esc(q)}</p><p class="a typing" id="live" dir="${qdir}">${esc(t.thinking)}</p><div class="sources" id="presrc"></div></article>`;
    let final = null;
    try {
      const r = await fetch("/api/ask/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Khazna-Session": sid },
        body: JSON.stringify({ question: q, role }),
      });
      if (r.status === 429) { toast(t.rate); throw new Error("rate"); }
      if (!r.ok || !r.body) throw new Error(`HTTP ${r.status}`);
      const reader = r.body.getReader();
      const dec = new TextDecoder();
      let buf = "", streamed = "";
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        let i;
        while ((i = buf.indexOf("\n\n")) >= 0) {
          const line = buf.slice(0, i).trim();
          buf = buf.slice(i + 2);
          if (!line.startsWith("data:")) continue;
          const ev = JSON.parse(line.slice(5));
          const live = $("#live");
          if (ev.type === "sources" && live) {
            live.textContent = meta && meta.generator === "llm" ? t.writing : t.thinking;
            $("#presrc").innerHTML = ev.sources.map((s) => `<div class="src"><header><span class="t"><span class="n">${s.n}</span>${esc(s.title)}</span><span class="s">${esc(s.section)}</span></header></div>`).join("");
          } else if (ev.type === "token" && live) {
            streamed += ev.text;
            live.innerHTML = richText(streamed, false);
          } else if (ev.type === "final") {
            final = ev;
          }
        }
      }
      if (!final) throw new Error("no answer");
      session.questions += 1;
      session.masked += Object.values(final.masked || {}).reduce((a, b) => a + b, 0) +
        final.sources.filter((s) => s.cited).reduce((a, s) => a + Object.values(s.masked || {}).reduce((x, y) => x + y, 0), 0);
      session.injections += final.injections_blocked || 0;
      lastAnswer = final;
      renderAnswer(final);
      refreshPrivacy();
    } catch (e) {
      if (e.message !== "rate") toast(t.toast_err);
      out.innerHTML = "";
    } finally {
      asking = false;
      if (btn) btn.disabled = false;
    }
  }

  function renderAnswer(a) {
    const t = T();
    const out = $("#out");
    if (!out) return;
    const qdir = isAr(a.question) ? "rtl" : "ltr";
    const adir = isAr(a.answer) ? "rtl" : "ltr";
    const maskedN = Object.values(a.masked || {}).reduce((x, y) => x + y, 0) +
      a.sources.filter((s) => s.cited).reduce((x, s) => x + Object.values(s.masked || {}).reduce((p, q) => p + q, 0), 0);
    const badges = [];
    if (a.refused) badges.push(["stop", t.b_refused]);
    else badges.push(["ok", t.b_cited(a.citations.length)]);
    if (maskedN) badges.push(["warn", t.b_masked(maskedN)]);
    if (a.injections_blocked) badges.push(["warn", t.b_inj(a.injections_blocked)]);
    if (!a.refused) {
      if (a.method === "llm") badges.push(["plain", t.b_model(modelName())]);
      else if (a.method === "llm->extractive") badges.push(["plain", t.b_fallback]);
      else badges.push(["plain", t.b_quote]);
    }
    if (a.sources.some((s) => s.superseded)) badges.push(["plain", t.b_old]);
    badges.push(["plain", `${tx("b_local")} · ${a.ms} ms`]);

    const srcs = a.sources.map((s) => {
      const flags = [];
      if (s.cited) flags.push(`<span class="badge ok">${esc(t.cited)}</span>`);
      if (s.superseded) flags.push(`<span class="badge warn">${esc(t.superseded)}</span>`);
      const m = Object.values(s.masked || {}).reduce((x, y) => x + y, 0);
      if (m) flags.push(`<span class="badge warn">${esc(t.b_masked(m))}</span>`);
      if (s.injection_removed) flags.push(`<span class="badge stop">${esc(t.removed_note(s.injection_removed))}</span>`);
      const sdir = isAr(s.text) ? "rtl" : "ltr";
      return `<div class="src${s.cited ? " cited" : ""}" id="src-${s.n}">
        <header><span class="t"><span class="n">${s.n}</span>${esc(s.title)}</span><span class="s">${esc(s.section)} · <span class="cls ${esc(s.uploaded ? "up" : s.classification)}">${esc(s.classification)}</span></span></header>
        <p class="x" dir="${sdir}">${richText(s.text, false)}</p>
        <div class="flags">${flags.join("")}${s.uploaded ? "" : `<button type="button" class="open" data-doc="${esc(s.doc)}">${esc(t.open_doc)}</button>`}</div>
      </div>`;
    }).join("");

    out.innerHTML = `<article class="answer">
      <p class="q" dir="${qdir}">${esc(a.question)}</p>
      <p class="a${a.refused ? " refused" : ""}" dir="${adir}">${richText(a.answer, true)}</p>
      <div class="badges">${badges.map(([k, v]) => `<span class="badge ${k}">${esc(v)}</span>`).join("")}</div>
      ${a.sources.length ? `<h3 class="small muted" style="margin-top:22px">${esc(t.sources_h)}</h3><div class="sources">${srcs}</div>` : ""}
    </article>`;
    out.querySelectorAll(".cite").forEach((b) => b.addEventListener("click", () => {
      const el = $(`#src-${b.dataset.n}`);
      if (el) { el.scrollIntoView({ behavior: "smooth", block: "center" }); el.animate([{ outline: "2px solid #B08A3E" }, { outline: "2px solid transparent" }], { duration: 1200 }); }
    }));
    out.querySelectorAll("button.open").forEach((b) => b.addEventListener("click", () => openDoc(b.dataset.doc)));
  }

  // ------------------------------------------------------------------ Library + document drawer
  async function pageLibrary() {
    const t = T();
    main.innerHTML = `<div class="wrap"><h1>${esc(t.lib_h)}</h1><p class="lede" id="liblede"></p><div class="table-wrap" id="libt"><div class="loading">${esc(t.loading)}</div></div></div>`;
    let rows;
    try { rows = await api(`/api/library?role=${encodeURIComponent(role)}`); } catch (e) { toast(t.toast_err); return; }
    const company = rows.filter((r) => !r.uploaded);
    $("#liblede").innerHTML = t.lib_lede(esc(roleLabel(role)), company.filter((r) => r.can_read).length, company.length);
    rows.sort((a, b) => (b.can_read - a.can_read) || (a.uploaded - b.uploaded));
    $("#libt").innerHTML = `<table class="lib">
      <thead><tr><th>${esc(t.th_doc)}</th><th>${esc(t.th_cls)}</th><th>${esc(t.th_owner)}</th><th>${esc(t.th_access)}</th><th>${esc(t.th_pii)}</th></tr></thead>
      <tbody>${rows.map((r) => {
        const title = lang === "ar" && r.title_ar ? r.title_ar : r.title;
        const sub = lang === "ar" && r.title_ar ? r.title : r.title_ar;
        const old = r.status === "superseded" ? ` <span class="badge warn">${esc(t.old)}</span>` : "";
        const p = piiSummary(r.pii);
        return `<tr class="${r.can_read ? "" : "locked"}">
          <td class="tt">${esc(title)}${old}${sub ? `<small>${esc(sub)}</small>` : ""}</td>
          <td><span class="cls ${esc(r.uploaded ? "up" : r.classification)}">${esc(r.classification)}</span></td>
          <td>${esc(r.owner)}</td>
          <td class="lockcell">${r.can_read ? `<button type="button" class="open btn small ghost" data-doc="${esc(r.id)}">${esc(t.read)}</button>` : `🔒 ${esc(t.cannot)}`}</td>
          <td class="small">${r.can_read ? esc(p || t.none_pii) : "—"}</td>
        </tr>`;
      }).join("")}</tbody></table>`;
    main.querySelectorAll("button.open").forEach((b) => b.addEventListener("click", () => openDoc(b.dataset.doc)));
  }

  let lastFocus = null;
  function closeDrawer() {
    const d = $(".drawer-bg");
    if (d) {
      d.remove();
      document.removeEventListener("keydown", onDrawerKey);
      if (lastFocus) lastFocus.focus();
    }
  }
  function onDrawerKey(e) { if (e.key === "Escape") closeDrawer(); }

  function docHtml(d) {
    const t = T();
    const inj = new Set(d.injection_lines || []);
    const lines = d.text.split("\n");
    let html = "", para = [];
    const flush = () => { if (para.length) { html += `<p>${para.join("<br>")}</p>`; para = []; } };
    for (const raw of lines) {
      const line = raw.trim();
      if (!line) { flush(); continue; }
      if (inj.has(line)) { flush(); html += `<div class="inj"><b>${esc(t.inj_h)}</b>${esc(t.inj_p)}<br><s>${esc(line)}</s></div>`; continue; }
      const h = line.match(/^#{1,4}\s+(.*)$/);
      if (h) { flush(); html += `<h3>${richText(h[1], false)}</h3>`; continue; }
      para.push(richText(line.replace(/^[-*]\s+/, "• ").replace(/\*\*(.+?)\*\*/g, "$1"), false));
    }
    flush();
    return html;
  }

  async function openDoc(id) {
    const t = T();
    let d;
    try { d = await api(`/api/documents/${encodeURIComponent(id)}?role=${encodeURIComponent(role)}`); } catch (e) { toast(t.toast_err); return; }
    closeDrawer();
    lastFocus = document.activeElement;
    const bg = document.createElement("div");
    bg.className = "drawer-bg";
    const m = Object.values(d.masked || {}).reduce((a, b) => a + b, 0);
    const ddir = d.lang === "ar" ? "rtl" : "ltr";
    bg.innerHTML = `<div class="drawer" role="dialog" aria-modal="true" aria-labelledby="dtitle">
      <button type="button" class="close">${esc(t.close)}</button>
      <span class="cls ${esc(d.classification)}">${esc(d.classification)}</span>
      <h2 id="dtitle" dir="${ddir}">${esc(lang === "ar" && d.title_ar ? d.title_ar : d.title)}</h2>
      <p class="small muted">${esc(d.owner)}</p>
      ${d.status === "superseded" ? `<p><span class="badge warn">${esc(t.doc_old)}</span></p>` : ""}
      ${m ? `<p><span class="badge warn">${esc(t.doc_masked(m))}</span></p>` : ""}
      <div class="doc" dir="${ddir}" lang="${d.lang === "ar" ? "ar" : "en"}">${docHtml(d)}</div>
    </div>`;
    bg.addEventListener("click", (e) => { if (e.target === bg) closeDrawer(); });
    $(".close", bg).addEventListener("click", closeDrawer);
    document.body.appendChild(bg);
    document.addEventListener("keydown", onDrawerKey);
    $(".close", bg).focus();
  }

  // ------------------------------------------------------------------ Upload page
  function pageUpload() {
    const t = T();
    const ttl = meta ? meta.upload_ttl_min : 30, mb = meta ? meta.max_upload_mb : 5;
    main.innerHTML = `<div class="wrap">
      <h1>${esc(t.up_h)}</h1>
      <p class="lede">${esc(tx("up_lede")(ttl, mb))}</p>
      <label class="drop" id="drop" tabindex="0">
        <strong>${esc(t.drop)}</strong><span class="muted">${esc(t.drop2)}</span>
        <input type="file" id="file" accept=".pdf,.docx,.txt,.md,text/plain,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" hidden>
      </label>
      <p id="upmsg" aria-live="polite"></p>
      <div class="uploads" id="uploads"></div>
      <section class="section">
        <h2>${esc(t.scan_h)}</h2>
        <p class="muted">${esc(t.scan_p)}</p>
        <div class="scanbox">
          <textarea id="scantext" rows="4" maxlength="5000" placeholder="${esc(t.scan_ph)}" aria-label="${esc(t.scan_h)}"></textarea>
          <button type="button" class="btn" id="scanbtn">${esc(t.scan_btn)}</button>
        </div>
        <div class="scanout" id="scanout" aria-live="polite"></div>
      </section>
    </div>`;
    const drop = $("#drop"), file = $("#file");
    drop.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); file.click(); } });
    ["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
    ["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
    drop.addEventListener("drop", (e) => { if (e.dataTransfer.files[0]) upload(e.dataTransfer.files[0]); });
    file.addEventListener("change", () => { if (file.files[0]) upload(file.files[0]); file.value = ""; });
    $("#scanbtn").addEventListener("click", scan);
    listUploads();
  }
  async function upload(f) {
    const t = T();
    const msg = $("#upmsg");
    msg.textContent = "…";
    const fd = new FormData();
    fd.append("file", f, f.name);
    try {
      const r = await api("/api/upload", { method: "POST", body: fd });
      const p = piiSummary(r.pii);
      msg.innerHTML = `<span class="badge ok">${esc(t.up_ok(r.title, r.words))}</span>${p ? ` <span class="badge warn">${esc(t.up_pii(p))}</span>` : ""}`;
      listUploads();
    } catch (e) {
      msg.innerHTML = `<span class="badge stop">${esc(t.err_upload)}: ${esc(e.message)}</span>`;
    }
  }
  async function listUploads() {
    const t = T();
    let rows;
    try { rows = (await api(`/api/library?role=${encodeURIComponent(role)}`)).filter((r) => r.uploaded); } catch (e) { return; }
    const el = $("#uploads");
    if (!el) return;
    if (!rows.length) { el.innerHTML = `<p class="empty">${esc(t.up_none)}</p>`; return; }
    el.innerHTML = rows.map((r) => `<div class="upl">
      <div><b>${esc(r.title)}</b><br><span class="small muted">${r.words} · ${esc(t.up_expires(r.expires_in_min))}${piiSummary(r.pii) ? " · " + esc(t.up_pii(piiSummary(r.pii))) : ""}</span></div>
      <div><button type="button" class="btn small ghost" data-open="${esc(r.id)}">${esc(t.read)}</button>
      <a class="btn small" href="#/">${esc(t.up_ask)}</a>
      <button type="button" class="btn small ghost" data-del="${esc(r.id)}">${esc(t.up_del)}</button></div>
    </div>`).join("");
    el.querySelectorAll("[data-open]").forEach((b) => b.addEventListener("click", () => openDoc(b.dataset.open)));
    el.querySelectorAll("[data-del]").forEach((b) => b.addEventListener("click", async () => {
      try { await api(`/api/upload/${encodeURIComponent(b.dataset.del)}`, { method: "DELETE" }); toast(t.deleted); listUploads(); } catch (e) { toast(t.toast_err); }
    }));
  }
  async function scan() {
    const t = T();
    const text = $("#scantext").value.trim();
    if (!text) return;
    try {
      const r = await api("/api/scan", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text, role: "employee" }) });
      const p = piiSummary(r.found);
      $("#scanout").innerHTML = `<p dir="auto">${richText(r.masked, false).replace(/\n/g, "<br>")}</p>${p ? `<span class="badge warn">${esc(t.b_masked(Object.values(r.found).reduce((a, b) => a + b, 0)))}: ${esc(p)}</span>` : ""}`;
    } catch (e) { if (e.message !== "rate") toast(t.toast_err); }
  }

  // ------------------------------------------------------------------ Evidence page
  async function pageEvidence() {
    const t = T();
    main.innerHTML = `<div class="wrap"><h1>${esc(t.ev_h)}</h1><div class="loading">${esc(t.loading)}</div></div>`;
    let ev;
    try { ev = await api("/api/eval"); } catch (e) { toast(t.toast_err); return; }
    const r = ev.results;
    if (!r) { main.innerHTML = `<div class="wrap"><h1>${esc(t.ev_h)}</h1><p class="empty">–</p></div>`; return; }
    const L = ev.results_llm;
    const leaks = ["restricted", "pii", "injection", "superseded"];
    const totalLeaks = leaks.reduce((a, k) => a + (r.leaks[k] || 0), 0);
    const bar = (x) => `<div class="bar" aria-hidden="true"><i style="width:${Math.round((x || 0) * 100)}%"></i></div>`;
    const rowsA = [
      ["acc", r.answers.accuracy, L && L.answers.accuracy],
      ["en", r.answers.english_accuracy, L && L.answers.english_accuracy],
      ["ar", r.answers.arabic_accuracy, L && L.answers.arabic_accuracy],
      ["cross", r.answers.cross_accuracy, L && L.answers.cross_accuracy],
      ["ver", r.answers.version_accuracy, L && L.answers.version_accuracy],
      ["unans", r.refusal.unanswerable, L && L.refusal.unanswerable],
      ["restr", r.refusal.restricted, L && L.refusal.restricted],
    ];
    main.innerHTML = `<div class="wrap">
      <h1>${esc(t.ev_h)}</h1>
      <p class="lede">${esc(t.ev_lede(r.rows.length))}</p>
      <div class="figs">
        <div class="fig"><div class="v">${pct(r.answers.accuracy)}</div><p>${esc(t.ev_f1)}</p></div>
        <div class="fig"><div class="v">${pct(r.answers.cross_accuracy)}</div><p>${esc(t.ev_f2)}</p></div>
        <div class="fig"><div class="v">${pct(r.refusal.unanswerable)}</div><p>${esc(t.ev_f3)}</p></div>
        <div class="fig"><div class="v">${totalLeaks}</div><p>${esc(t.ev_f4)}</p></div>
      </div>
      <section class="section">
        <h2>${esc(t.ev_leaks)}</h2>
        <p class="muted">${esc(t.ev_leaks_p(r.leaks.checks))}</p>
        <div class="table-wrap"><table class="tbl"><tbody>
          ${leaks.map((k) => `<tr><td>${esc(t.lk[k])}</td><td class="${r.leaks[k] ? "" : "zero"}"><b>${r.leaks[k]}</b></td></tr>`).join("")}
        </tbody></table></div>
      </section>
      <section class="section">
        <h2>${esc(t.ev_ans)}</h2>
        <div class="table-wrap"><table class="tbl">
          <thead><tr><th></th><th>${esc(t.mode_builtin)}</th><th></th>${L ? `<th>${esc(t.mode_llm((L.model || "").split("/").pop() || "LLM"))}</th>` : ""}</tr></thead>
          <tbody>${rowsA.map(([k, a, b]) => `<tr><td>${esc(t.m[k])}</td><td><b>${pct(a)}</b></td><td>${bar(a)}</td>${L ? `<td><b>${pct(b)}</b></td>` : ""}</tr>`).join("")}
          <tr><td>${esc(t.m.p50)}</td><td><b>${r.latency_ms.p50} ms</b></td><td></td>${L && L.latency_ms ? `<td><b>${Math.round(L.latency_ms.p50)} ms</b></td>` : ""}</tr></tbody>
        </table></div>
        <p class="small muted">${esc(t.ev_note)}</p>
      </section>
      <section class="section">
        <h2>${esc(t.ev_ret)}</h2>
        <div class="table-wrap"><table class="tbl">
          <thead><tr>${t.ret_cols.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead>
          <tbody>${Object.entries(r.retrieval).map(([m, v]) => `<tr><td>${esc(m === "dense" ? "Dense (FAISS)" : m === "hybrid" ? "Hybrid (RRF)" : "BM25")}</td><td>${pct(v.hit1)}</td><td>${pct(v.hit5)}</td><td>${v.mrr.toFixed(2)}</td></tr>`).join("")}</tbody>
        </table></div>
      </section>
    </div>`;
  }

  // ------------------------------------------------------------------ How page
  function pageHow() {
    const t = T();
    main.innerHTML = `<div class="wrap">
      <h1>${esc(t.how_h)}</h1>
      <div class="flow">${t.flow.map(([h, p]) => `<div><b>${esc(h)}</b>${esc(p)}</div>`).join("")}</div>
      <div class="prose">${meta && meta.runtime === "browser" ? t.how_br : ""}${t.how_html()}</div>
      ${meta ? `<p class="small muted">${esc(meta.retrieval)} · ${meta.documents} / ${meta.passages}</p>` : ""}
    </div>`;
  }

  // ------------------------------------------------------------------ boot
  async function boot() {
    applyLang();
    try {
      meta = await api("/api/meta");
    } catch (e) {
      main.innerHTML = `<div class="wrap"><p class="empty">${esc(T().toast_err)}</p></div>`;
      return;
    }
    fillRoles();
    route();
  }
  boot();
})();
