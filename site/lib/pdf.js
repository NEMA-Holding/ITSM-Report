/* Download PDF: saves the report exactly as filtered on screen.
   Summary sections are captured as pictures; the ticket and change lists are written as real tables,
   so every row is included however long the list is. Libraries load only when the button is pressed. */
(function () {
  var LIBS = ["../lib/html2canvas.min.js", "../lib/jspdf.umd.min.js", "../lib/jspdf.plugin.autotable.min.js"];
  var LISTS = "#regTable,#cregTable";

  function load(src) {
    return new Promise(function (ok, fail) {
      if (document.querySelector('script[data-pdflib="' + src + '"]')) return ok();
      var s = document.createElement("script");
      s.src = src; s.dataset.pdflib = src; s.onload = ok;
      s.onerror = function () { fail(new Error("Could not load " + src)); };
      document.head.appendChild(s);
    });
  }
  function shown(el) { return el && el.getClientRects().length > 0 && getComputedStyle(el).visibility !== "hidden"; }
  function pad(n) { return String(n).padStart(2, "0"); }
  function clean(t) {
    return t.replace(/[\u2018\u2019]/g, "'").replace(/[\u201C\u201D]/g, '"').replace(/[\u2013\u2014]/g, "-").replace(/\u2026/g, "...")
      .replace(/[^\x20-\x7E\u00A0-\u00FF]/g, "").replace(/\s+/g, " ").trim();
  }

  async function build(btn) {
    for (var i = 0; i < LIBS.length; i++) await load(LIBS[i]);
    var root = document.documentElement, prevTheme = root.getAttribute("data-theme");
    root.setAttribute("data-theme", "light");                     // always print in light colours
    root.classList.add("pdf-capture");
    try {
      var doc = new window.jspdf.jsPDF({ orientation: "landscape", unit: "pt", format: "a4", compress: true });
      var W = doc.internal.pageSize.getWidth(), H = doc.internal.pageSize.getHeight(), M = 26, FOOT = 22;
      var y = M, bg = "#ffffff";                                   // plain white behind every captured section

      function room(h) { if (y + h > H - M - FOOT) { doc.addPage(); y = M; } }

      async function picture(el) {
        var c = await window.html2canvas(el, {
          scale: 2, backgroundColor: bg, logging: false, useCORS: true,
          ignoreElements: function (n) { return n.matches && n.matches("button.mini, .pdf-skip"); }
        });
        var w = W - 2 * M, scale = w / c.width, full = H - 2 * M - FOOT, srcY = 0;
        var h = c.height * scale;
        if (h <= full) { room(h); doc.addImage(c.toDataURL("image/jpeg", 0.92), "JPEG", M, y, w, h); y += h + 10; return; }
        while (srcY < c.height) {                                    // tall section: continue across pages
          room(60); var avail = H - M - FOOT - y, sliceH = Math.min(c.height - srcY, Math.floor(avail / scale));
          var part = document.createElement("canvas"); part.width = c.width; part.height = sliceH;
          part.getContext("2d").drawImage(c, 0, srcY, c.width, sliceH, 0, 0, c.width, sliceH);
          doc.addImage(part.toDataURL("image/jpeg", 0.92), "JPEG", M, y, w, sliceH * scale);
          y += sliceH * scale + 10; srcY += sliceH;
          if (srcY < c.height) { doc.addPage(); y = M; }
        }
      }

      function list(panel, table) {
        var h2 = panel.querySelector("h2");
        room(70);
        if (h2) {
          doc.setFont("helvetica", "bold"); doc.setFontSize(12); doc.setTextColor(24, 90, 125);
          doc.text(h2.textContent.trim(), M, y + 12); y += 22;
        }
        doc.autoTable({
          html: table, startY: y, margin: { left: M, right: M, bottom: M + FOOT }, theme: "grid",
          styles: { font: "helvetica", fontSize: 7.5, cellPadding: 3, overflow: "linebreak", lineColor: [221, 230, 235], lineWidth: 0.4, textColor: [30, 30, 30] },
          headStyles: { fillColor: [24, 90, 125], textColor: 255, fontStyle: "bold" },
          alternateRowStyles: { fillColor: [245, 248, 250] },
          didParseCell: function (d) {                                // keep words apart, drop symbols the PDF font cannot draw
            var el = d.cell.raw; if (!el || !el.childNodes) return;
            var parts = [].map.call(el.childNodes, function (n) { return (n.textContent || "").trim(); }).filter(Boolean);
            d.cell.text = [clean(parts.join(" · "))];
          }
        });
        y = doc.lastAutoTable.finalY + 14;
      }

      async function walk(el) {
        if (!shown(el) || el.matches("script,style,.pdf-skip,.views")) return;
        var t = el.querySelector(LISTS), shownList = t && shown(t) ? t : null;
        if (!shownList) return picture(el);
        var panel = shownList.closest(".panel") || shownList.parentElement;
        if (el === panel) return list(panel, shownList);
        for (var k = 0; k < el.children.length; k++) await walk(el.children[k]);
      }

      var wrap = document.querySelector(".wrap");
      for (var k = 0; k < wrap.children.length; k++) await walk(wrap.children[k]);

      var d = new Date(), stamp = d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()) + " " + pad(d.getHours()) + ":" + pad(d.getMinutes());
      var title = (document.querySelector("h1") || {}).textContent || document.title;
      title = title.replace(/\s+/g, " ").trim();
      var n = doc.getNumberOfPages();
      for (var p = 1; p <= n; p++) {
        doc.setPage(p); doc.setFont("helvetica", "normal"); doc.setFontSize(8); doc.setTextColor(110, 120, 128);
        doc.text(title + " · downloaded " + stamp + " (UAE)", M, H - 12);
        doc.text("Page " + p + " of " + n, W - M, H - 12, { align: "right" });
      }
      doc.save(title + " " + stamp.replace(":", "") + ".pdf");
    } finally {
      root.classList.remove("pdf-capture");
      if (prevTheme === null) root.removeAttribute("data-theme"); else root.setAttribute("data-theme", prevTheme);
    }
  }

  var st = document.createElement("style");
  st.textContent = ".pdf-capture *,.pdf-capture *::before,.pdf-capture *::after{animation:none!important;transition:none!important;box-shadow:none!important}"
    + ".pdf-capture button.kpi.on{outline:2px solid #185a7d;outline-offset:-2px}"
    + ".pdf-capture header{margin:0!important;padding:20px 22px 18px!important;border-radius:8px!important}"
    + ".pdf-capture header .hbg,.pdf-capture header .hveil{display:none!important}";
  document.head.appendChild(st);

  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("pdfBtn"); if (!btn) return;
    btn.addEventListener("click", async function () {
      if (btn.disabled) return;
      var label = btn.textContent; btn.disabled = true; btn.textContent = "Preparing PDF…";
      try { await build(btn); btn.textContent = "PDF downloaded"; }
      catch (e) { console.error(e); btn.textContent = "PDF failed – try again"; }
      setTimeout(function () { btn.disabled = false; btn.textContent = label; }, 2500);
    });
  });
})();
