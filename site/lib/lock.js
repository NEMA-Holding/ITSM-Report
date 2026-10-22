/* Ticket details behind a log in.
   The public data files hold no subjects, requester names or change titles. Those are in data/detail.json,
   encrypted with AES-256-GCM; the key is derived from the report password (PBKDF2-SHA256), so without the
   password the file cannot be read. After log in the details are decrypted in the browser and the ticket
   list is shown. The password is kept only for this browser tab (sessionStorage) until Log out. */
(function () {
  var LISTS = [["regTable", "Ticket details"], ["cregTable", "Change request details"]];
  var KEY = "itsm-report-pass";
  var DET = null, pass = null, busy = null;
  var $ = function (id) { return document.getElementById(id); };
  if (!$("regTable")) return;

  var css = document.createElement("style");
  css.textContent =
    "body.locked .has-details{display:none!important}body:not(.locked) .lockcard{display:none!important}" +
    "section.panel.lockcard{display:flex;flex-wrap:wrap;align-items:center;gap:14px 18px;border:1px dashed var(--line)}" +
    ".lockcard .ic{flex:none;width:44px;height:44px;border-radius:50%;display:grid;place-items:center;background:var(--accent-soft);color:var(--accent)}" +
    ".lockcard .lt{flex:1 1 260px;display:grid;gap:3px}.lockcard .lt b{color:var(--accent);font-size:15px}.lockcard .lt span{color:var(--muted);font-size:13px}" +
    ".lockcard button{width:auto;padding:9px 18px}" +
    "dialog.login{border:0;border-radius:12px;padding:0;width:min(380px,calc(100% - 32px));background:var(--surface);color:var(--fg);box-shadow:0 20px 60px rgba(0,0,0,.35)}" +
    "dialog.login::backdrop{background:rgba(8,20,30,.55)}" +
    "dialog.login form{display:grid;gap:12px;padding:22px}dialog.login h2{margin:0;font-size:17px;color:var(--accent)}" +
    "dialog.login p{margin:0;font-size:13px;color:var(--muted)}dialog.login label{display:grid;gap:5px;font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--accent)}" +
    "dialog.login input{font:15px Arial,sans-serif;padding:9px 10px}" +
    "dialog.login .err{color:var(--viol);font-size:13px;font-weight:700;min-height:1.2em}dialog.login .row{display:flex;gap:10px;justify-content:flex-end}" +
    "dialog.login .row button{width:auto;padding:9px 16px}dialog.login .row .go{background:var(--accent);color:#fff}";
  document.head.appendChild(css);

  var LOCK_SVG = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>';

  // restricted box in place of each detail list
  LISTS.forEach(function (l) {
    var t = $(l[0]); if (!t) return;
    var panel = t.closest(".panel") || t.parentElement; panel.classList.add("has-details");
    var card = document.createElement("section"); card.className = "panel lockcard";
    card.innerHTML = '<span class="ic">' + LOCK_SVG + '</span><span class="lt"><b>' + l[1] + ' are restricted</b>' +
      '<span>Log in to see ticket subjects, requesters and the full list. The figures above are open to everyone.</span></span>' +
      '<button type="button" class="pdf-skip">Log in</button>';
    card.querySelector("button").onclick = ask;
    panel.parentNode.insertBefore(card, panel);
  });
  document.body.classList.add("locked");

  // header button next to Download PDF
  var anchor = $("pdfBtn") || $("refresh");
  var hb = document.createElement("button"); hb.type = "button"; hb.id = "loginBtn";
  hb.className = anchor.classList.contains("tbtn") ? "tbtn" : "mini";
  anchor.parentNode.insertBefore(hb, anchor);                       // Log in sits just before Download PDF
  function label() { hb.textContent = DET ? "Log out" : "🔒 Log in"; hb.title = DET ? "Hide ticket details again" : "Log in to see ticket details"; }
  hb.onclick = function () { if (DET) logout(); else ask(); };
  label();

  // log in dialog
  var dlg = document.createElement("dialog"); dlg.className = "login";
  dlg.innerHTML = '<form method="dialog"><h2>Log in to see ticket details</h2><p>Enter the ITSM report password.</p>' +
    '<label>Password<input type="password" name="pw" autocomplete="current-password" required></label>' +
    '<div class="err" role="alert"></div><div class="row"><button type="button" class="cancel">Cancel</button><button type="submit" class="go">Log in</button></div></form>';
  document.body.appendChild(dlg);
  var form = dlg.querySelector("form"), input = form.pw, err = dlg.querySelector(".err"), go = dlg.querySelector(".go");
  dlg.querySelector(".cancel").onclick = function () { dlg.close(); };
  form.addEventListener("submit", async function (e) {
    e.preventDefault(); err.textContent = ""; go.disabled = true; go.textContent = "Checking…";
    var pw = input.value.trim();
    try { await unlock(pw); store(pw); dlg.close(); input.value = ""; }
    catch (x) { err.textContent = x && x.message === "nodata" ? "Ticket details are not available yet." : "Incorrect password."; input.select(); }
    go.disabled = false; go.textContent = "Log in";
  });
  function ask() { err.textContent = ""; if (dlg.showModal) dlg.showModal(); else dlg.setAttribute("open", ""); input.focus(); }

  // decryption
  function b64(s) { var b = atob(s), u = new Uint8Array(b.length); for (var i = 0; i < b.length; i++) u[i] = b.charCodeAt(i); return u; }
  async function decrypt(pw) {
    var r = await fetch("data/detail.json?t=" + Date.now(), { cache: "no-store" });
    if (!r.ok) throw new Error("nodata");
    var j = await r.json(), enc = new TextEncoder();
    var base = await crypto.subtle.importKey("raw", enc.encode(pw), "PBKDF2", false, ["deriveKey"]);
    var key = await crypto.subtle.deriveKey({ name: "PBKDF2", hash: "SHA-256", salt: b64(j.salt), iterations: j.iter },
      base, { name: "AES-GCM", length: 256 }, false, ["decrypt"]);
    var plain = await crypto.subtle.decrypt({ name: "AES-GCM", iv: b64(j.iv) }, key, b64(j.ct));
    return JSON.parse(new TextDecoder().decode(plain));
  }
  async function unlock(pw) { DET = await decrypt(pw); pass = pw; document.body.classList.remove("locked"); label(); rerender(); }
  function logout() { DET = null; pass = null; try { sessionStorage.removeItem(KEY); } catch (_) {} document.body.classList.add("locked"); label(); rerender(); }
  function store(pw) { try { sessionStorage.setItem(KEY, pw); } catch (_) {} }

  // put the details back into the rows the page draws from
  var baseLoad = window.load, baseSetCH = window.setCH;
  window.load = function (rows) {
    var missing = 0;
    if (DET && DET.t) rows = rows.map(function (r) { var d = DET.t[r[0]]; if (!d) { missing++; return r; } r = r.slice(); r[1] = d[0]; r[7] = d[1]; return r; });
    if (missing && pass && !busy) busy = decrypt(pass).then(function (d) { DET = d; busy = null; rerender(); }, function () { busy = null; });
    var a = [].slice.call(arguments); a[0] = rows; return baseLoad.apply(this, a);
  };
  if (typeof baseSetCH === "function") window.setCH = function (rows) {
    if (DET && DET.c) rows = rows.map(function (r) { var t = DET.c[r[0]]; if (t == null) return r; r = r.slice(); r[1] = t; return r; });
    return baseSetCH.call(this, rows);
  };
  function rerender() {
    if (typeof window.setCH === "function") window.setCH(window.CHG || []);
    window.load(window.SNAP || [], window.SNAP_ASOF || 0, "live");
  }

  // already logged in earlier in this tab
  var saved = null; try { saved = sessionStorage.getItem(KEY); } catch (_) {}
  if (saved) unlock(saved).catch(function () { try { sessionStorage.removeItem(KEY); } catch (_) {} });
})();
