"""
M3 — Construit dashboard/index.html (brutalist edition).

Pipeline : DuckDB agrège → on convertit en JSON → on l'injecte dans un
template HTML. Charts hand-rolled en SVG, interactivité en vanilla JS.
"""

import json
from pathlib import Path

import duckdb

CHEMIN_CSV = "data/depenses.csv"
SORTIE = Path("dashboard") / "index.html"


def main():
    con = duckdb.connect(":memory:")
    con.execute(f"""
        create view t as
        select * from read_csv_auto('{CHEMIN_CSV}', header=true)
    """)

    par_mois = con.execute("""
        select strftime(date_trunc('month', date), '%Y-%m') as mois,
               round(sum(montant), 2) as total
        from t group by 1 order by 1
    """).fetchall()

    par_cat = con.execute("""
        select categorie, round(sum(montant), 2) as total
        from t group by 1 order by total desc
    """).fetchall()

    merchants_full = con.execute("""
        select marchand, categorie,
               round(sum(montant), 2) as total,
               count(*) as nb
        from t group by 1, 2 order by total desc
    """).fetchall()

    pivot_brut = con.execute("""
        select strftime(date_trunc('month', date), '%Y-%m') as mois,
               categorie,
               round(sum(montant), 2) as total
        from t group by 1, 2 order by 1, 2
    """).fetchall()

    stats = con.execute("""
        select round(sum(montant), 2) as total,
               count(*) as nb,
               round(sum(montant) / 15, 2) as moy_mois
        from t
    """).fetchone()

    mois_labels = [r[0] for r in par_mois]
    cat_labels = [r[0] for r in par_cat]

    pivot = {c: [0.0] * len(mois_labels) for c in cat_labels}
    idx = {m: i for i, m in enumerate(mois_labels)}
    for mois, cat, total in pivot_brut:
        pivot[cat][idx[mois]] = total

    payload = {
        "mois": mois_labels,
        "cat_labels": cat_labels,
        "pivot": pivot,
        "merchants_full": [
            {"nom": m[0], "categorie": m[1], "total": m[2], "nb": m[3]}
            for m in merchants_full
        ],
        "stats": {"total": stats[0], "nb": stats[1], "moy_mois": stats[2]},
    }

    html = TEMPLATE.replace("__DATA_JSON__", json.dumps(payload, ensure_ascii=False))
    SORTIE.parent.mkdir(exist_ok=True)
    SORTIE.write_text(html, encoding="utf-8")
    print(f"Dashboard écrit : {SORTIE}  ({SORTIE.stat().st_size:,} octets)")


# ---------- Template HTML brutalist ----------
TEMPLATE = r"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>DEPENSES // TERMINAL</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&display=swap" rel="stylesheet" />
  <style>
    :root {
      --bg: #000;
      --fg: #d4d6d9;
      --dim: #6e7378;
      --line: #2a2a2a;
      --line-soft: #1a1a1a;
      --accent: #ff8c42;
    }
    * { box-sizing: border-box; }
    html, body { margin: 0; padding: 0; }
    body {
      background: var(--bg);
      color: var(--fg);
      font-family: "Space Mono", ui-monospace, monospace;
      font-size: 13px;
      line-height: 1.5;
      padding: 28px 24px 64px;
      max-width: 1100px;
      margin: 0 auto;
    }
    .dim { color: var(--dim); }
    .accent { color: var(--accent); }

    /* Header */
    .header-line {
      font-weight: 700;
      letter-spacing: 0.04em;
      font-size: 14px;
    }
    .header-sub {
      color: var(--dim);
      font-size: 11px;
      margin-top: 4px;
      letter-spacing: 0.04em;
    }

    /* Stats */
    .stats {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      border: 1px solid var(--line);
      margin-top: 20px;
    }
    .stat {
      padding: 14px 16px;
      border-right: 1px solid var(--line);
    }
    .stat:last-child { border-right: none; }
    .stat-key {
      color: var(--dim);
      font-size: 10px;
      letter-spacing: 0.10em;
      text-transform: uppercase;
    }
    .stat-val {
      margin-top: 4px;
      font-weight: 700;
      font-size: 18px;
      color: var(--accent);
      font-variant-numeric: tabular-nums;
      word-break: break-word;
    }
    @media (max-width: 720px) {
      .stats { grid-template-columns: repeat(2, 1fr); }
      .stat { border-bottom: 1px solid var(--line); }
      .stat:nth-child(odd) { border-right: 1px solid var(--line); }
      .stat:nth-child(even) { border-right: none; }
    }

    /* Period selector */
    .period {
      display: flex;
      gap: 4px;
      margin-top: 18px;
      flex-wrap: wrap;
    }
    .period-btn {
      background: transparent;
      color: var(--dim);
      border: 1px solid var(--line);
      padding: 6px 12px;
      cursor: pointer;
      font-family: inherit;
      font-size: 12px;
      letter-spacing: 0.04em;
      transition: color 80ms, border-color 80ms;
    }
    .period-btn:hover { color: var(--fg); border-color: var(--dim); }
    .period-btn.active {
      color: var(--accent);
      border-color: var(--accent);
    }

    /* Section titles */
    h2 {
      font-family: inherit;
      font-weight: 700;
      font-size: 11px;
      letter-spacing: 0.14em;
      color: var(--dim);
      margin: 28px 0 8px;
      text-transform: uppercase;
    }

    /* Category rows */
    .cats { display: flex; flex-direction: column; border: 1px solid var(--line); }
    .cat-row {
      display: grid;
      grid-template-columns: 28px 1.5fr 1.3fr 110px 60px;
      align-items: center;
      gap: 12px;
      padding: 8px 12px;
      cursor: pointer;
      border-bottom: 1px solid var(--line-soft);
      transition: background 80ms;
    }
    .cat-row:last-child { border-bottom: none; }
    .cat-row:hover { background: #0a0a0a; }
    .cat-row.off .cat-name { text-decoration: line-through; opacity: 0.4; }
    .cat-row.off .cat-total, .cat-row.off .cat-pct { opacity: 0.35; }
    .cat-row.off .cat-bar-fill { opacity: 0.2; }
    .cat-box { color: var(--accent); user-select: none; font-weight: 700; }
    .cat-row.off .cat-box { color: var(--dim); }
    .cat-name {
      text-transform: uppercase;
      letter-spacing: 0.04em;
      font-size: 12px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .cat-bar { height: 10px; background: var(--line-soft); position: relative; }
    .cat-bar-fill { height: 100%; background: var(--dim); transition: width 200ms ease-out; }
    .cat-row[data-cat="Tech & outils dev"] .cat-bar-fill { background: var(--accent); }
    .cat-total { text-align: right; font-variant-numeric: tabular-nums; }
    .cat-pct { text-align: right; color: var(--dim); font-size: 11px; }

    /* Chart blocks */
    .chart-block { border: 1px solid var(--line); padding: 14px; margin-top: 10px; position: relative; }
    svg.chart { display: block; width: 100%; height: auto; }

    /* Merchants */
    .merch-list { border: 1px solid var(--line); }
    .merch-row {
      display: grid;
      grid-template-columns: 1.6fr 2fr 110px;
      align-items: center;
      gap: 12px;
      padding: 7px 12px;
      border-bottom: 1px solid var(--line-soft);
      font-size: 12px;
    }
    .merch-row:last-child { border-bottom: none; }
    .merch-name { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .merch-bar { height: 10px; background: var(--line-soft); position: relative; }
    .merch-fill { display: block; height: 100%; }
    .merch-val { text-align: right; font-variant-numeric: tabular-nums; }

    /* Tooltip */
    .tt {
      position: absolute;
      pointer-events: none;
      background: #0a0a0a;
      border: 1px solid var(--accent);
      color: var(--fg);
      padding: 6px 10px;
      font-size: 11px;
      white-space: nowrap;
      transform: translate(-50%, -120%);
      display: none;
      z-index: 10;
    }
    .tt strong { color: var(--accent); }

    /* Footer */
    footer {
      margin-top: 40px;
      padding-top: 16px;
      border-top: 1px dashed var(--line);
      color: var(--dim);
      font-size: 11px;
      letter-spacing: 0.06em;
    }
  </style>
</head>
<body>
  <div class="header-line">
    DEPENSES <span class="dim">//</span> <span id="h-period">…</span> <span class="dim">//</span> <span id="h-nb">…</span>
  </div>
  <div class="header-sub">// terminal de comptable nostalgique // ambre + gris froid // seed = 42</div>

  <div class="stats">
    <div class="stat"><div class="stat-key">TOTAL</div><div class="stat-val" id="h-total">…</div></div>
    <div class="stat"><div class="stat-key">AVG / MO</div><div class="stat-val" id="h-avg">…</div></div>
    <div class="stat"><div class="stat-key">TOP CAT</div><div class="stat-val" id="h-top">…</div></div>
    <div class="stat"><div class="stat-key">TECH SHARE</div><div class="stat-val" id="h-tech">…</div></div>
  </div>

  <div class="period">
    <button class="period-btn" data-period="3">[1] 3M</button>
    <button class="period-btn" data-period="6">[2] 6M</button>
    <button class="period-btn" data-period="12">[3] 12M</button>
    <button class="period-btn" data-period="all">[4] ALL</button>
  </div>

  <h2>// categories — click to toggle</h2>
  <div class="cats" id="cats"></div>

  <h2>// monthly evolution</h2>
  <div class="chart-block">
    <svg id="chart-line" class="chart" viewBox="0 0 1000 240" preserveAspectRatio="none"></svg>
    <div class="tt" id="tt-line"></div>
  </div>

  <h2>// monthly stacked by category</h2>
  <div class="chart-block">
    <svg id="chart-stacked" class="chart" viewBox="0 0 1000 280" preserveAspectRatio="none"></svg>
    <div class="tt" id="tt-stack"></div>
  </div>

  <h2>// top 10 merchants (filtered by enabled categories)</h2>
  <div class="merch-list" id="merchants-list"></div>

  <footer>
    CMDS · [1] 3M · [2] 6M · [3] 12M · [4] ALL · click any row to toggle a category
  </footer>

  <script id="data" type="application/json">__DATA_JSON__</script>
  <script>
  (() => {
    const D = JSON.parse(document.getElementById("data").textContent);
    const STATE = {
      enabled: new Set(D.cat_labels),
      period: "all",
    };

    const COULEURS = {
      "Tech & outils dev":   "#ff8c42",
      "Logement & factures": "#b8bcc1",
      "Loisirs & divers":    "#989ca0",
      "Courses":             "#777b7f",
      "Santé & sport":       "#5a5d60",
      "Transport":           "#454850",
      "Restos & cafés":      "#363a3e",
      "Espace & astronomie": "#fbb47a",
      "Finance":             "#ffd3a9",
    };
    const couleur = (c) => COULEURS[c] || "#666";

    const $ = (s) => document.querySelector(s);
    const $$ = (s) => Array.from(document.querySelectorAll(s));
    const EUR0 = (n) => new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(Math.round(n));
    const PCT = (a, b) => (b ? (100 * a / b).toFixed(1) : "0.0");

    function buildCatRows() {
      const html = D.cat_labels.map(cat => `
        <div class="cat-row" data-cat="${cat}">
          <span class="cat-box">[x]</span>
          <span class="cat-name">${cat}</span>
          <span class="cat-bar"><span class="cat-bar-fill"></span></span>
          <span class="cat-total"></span>
          <span class="cat-pct"></span>
        </div>
      `).join("");
      $("#cats").innerHTML = html;
      $$(".cat-row").forEach(row => {
        row.addEventListener("click", () => {
          const cat = row.dataset.cat;
          if (STATE.enabled.has(cat)) STATE.enabled.delete(cat);
          else STATE.enabled.add(cat);
          renderAll();
        });
      });
    }

    function monthIndices() {
      const n = STATE.period === "all" ? D.mois.length : parseInt(STATE.period, 10);
      const start = Math.max(0, D.mois.length - n);
      const out = [];
      for (let i = start; i < D.mois.length; i++) out.push(i);
      return out;
    }

    function computeFiltered() {
      const indices = monthIndices();
      const months = indices.map(i => D.mois[i]);
      const monthlyTotals = indices.map(i => {
        let s = 0;
        for (const c of STATE.enabled) s += (D.pivot[c]?.[i] ?? 0);
        return s;
      });
      const catTotals = {};
      for (const c of D.cat_labels) {
        catTotals[c] = indices.reduce((s, i) => s + (D.pivot[c]?.[i] ?? 0), 0);
      }
      const totalEnabled = [...STATE.enabled].reduce((s, c) => s + catTotals[c], 0);
      const totalAll = D.cat_labels.reduce((s, c) => s + catTotals[c], 0);
      const merchants = D.merchants_full
        .filter(m => STATE.enabled.has(m.categorie))
        .slice(0, 10);
      return { indices, months, monthlyTotals, catTotals, totalEnabled, totalAll, merchants };
    }

    function niceTicks(max, count) {
      if (max <= 0) return [0];
      const raw = max / count;
      const exp = Math.floor(Math.log10(raw));
      const base = raw / Math.pow(10, exp);
      let nice;
      if (base < 1.5) nice = 1; else if (base < 3) nice = 2;
      else if (base < 7) nice = 5; else nice = 10;
      const step = nice * Math.pow(10, exp);
      const ticks = [];
      for (let v = 0; v <= max + step / 2; v += step) ticks.push(v);
      return ticks;
    }

    function drawLine(F) {
      const svg = $("#chart-line");
      const W = 1000, H = 240, PADL = 60, PADR = 20, PADT = 16, PADB = 32;
      const iw = W - PADL - PADR, ih = H - PADT - PADB;
      const max = Math.max(1, ...F.monthlyTotals);
      const ticks = niceTicks(max, 5);
      const top = ticks[ticks.length - 1] || max;
      const yScale = (v) => PADT + ih * (1 - v / top);
      const xScale = (i, n) => n <= 1 ? PADL + iw / 2 : PADL + iw * i / (n - 1);
      const parts = [];
      parts.push(`<line x1="${PADL}" x2="${W - PADR}" y1="${yScale(0)}" y2="${yScale(0)}" stroke="#2a2a2a"/>`);
      for (const t of ticks) {
        if (t === 0) continue;
        parts.push(`<line x1="${PADL}" x2="${W - PADR}" y1="${yScale(t)}" y2="${yScale(t)}" stroke="#1a1a1a" stroke-dasharray="2 4"/>`);
        parts.push(`<text x="${PADL - 8}" y="${yScale(t) + 3}" fill="#6e7378" text-anchor="end" font-size="10">${EUR0(t)}</text>`);
      }
      const stride = F.months.length > 12 ? 2 : 1;
      F.months.forEach((m, i) => {
        if (i % stride !== 0 && i !== F.months.length - 1) return;
        parts.push(`<text x="${xScale(i, F.months.length)}" y="${H - PADB + 16}" fill="#6e7378" text-anchor="middle" font-size="10">${m}</text>`);
      });
      const pts = F.monthlyTotals.map((v, i) => `${xScale(i, F.months.length)},${yScale(v)}`).join(" ");
      parts.push(`<polyline points="${pts}" fill="none" stroke="#ff8c42" stroke-width="1.5"/>`);
      F.monthlyTotals.forEach((v, i) => {
        const x = xScale(i, F.months.length), y = yScale(v);
        parts.push(`<rect x="${x - 3}" y="${y - 3}" width="6" height="6" fill="#ff8c42"/>`);
      });
      svg.innerHTML = parts.join("");

      const tt = $("#tt-line");
      svg.onmousemove = (e) => {
        const rect = svg.getBoundingClientRect();
        const sx = (e.clientX - rect.left) * (W / rect.width);
        let bestI = 0, bestD = Infinity;
        F.months.forEach((_, i) => {
          const px = xScale(i, F.months.length);
          const d = Math.abs(px - sx);
          if (d < bestD) { bestD = d; bestI = i; }
        });
        tt.style.display = "block";
        tt.style.left = ((xScale(bestI, F.months.length) / W) * rect.width) + "px";
        tt.style.top = ((yScale(F.monthlyTotals[bestI]) / H) * rect.height) + "px";
        tt.innerHTML = `<strong>${F.months[bestI]}</strong> · ${EUR0(F.monthlyTotals[bestI])} EUR`;
      };
      svg.onmouseleave = () => { tt.style.display = "none"; };
    }

    function drawStacked(F) {
      const svg = $("#chart-stacked");
      const W = 1000, H = 280, PADL = 60, PADR = 20, PADT = 16, PADB = 32;
      const iw = W - PADL - PADR, ih = H - PADT - PADB;
      const sums = F.indices.map(i => {
        let s = 0;
        for (const c of STATE.enabled) s += (D.pivot[c]?.[i] ?? 0);
        return s;
      });
      const max = Math.max(1, ...sums);
      const ticks = niceTicks(max, 5);
      const top = ticks[ticks.length - 1] || max;
      const yScale = (v) => PADT + ih * (1 - v / top);
      const slot = iw / Math.max(1, F.months.length);
      const barW = slot * 0.7;
      const parts = [];
      parts.push(`<line x1="${PADL}" x2="${W - PADR}" y1="${yScale(0)}" y2="${yScale(0)}" stroke="#2a2a2a"/>`);
      for (const t of ticks) {
        if (t === 0) continue;
        parts.push(`<line x1="${PADL}" x2="${W - PADR}" y1="${yScale(t)}" y2="${yScale(t)}" stroke="#1a1a1a" stroke-dasharray="2 4"/>`);
        parts.push(`<text x="${PADL - 8}" y="${yScale(t) + 3}" fill="#6e7378" text-anchor="end" font-size="10">${EUR0(t)}</text>`);
      }
      const stride = F.months.length > 12 ? 2 : 1;
      F.months.forEach((m, i) => {
        if (i % stride !== 0 && i !== F.months.length - 1) return;
        parts.push(`<text x="${PADL + slot * i + slot / 2}" y="${H - PADB + 16}" fill="#6e7378" text-anchor="middle" font-size="10">${m}</text>`);
      });
      F.indices.forEach((origI, i) => {
        let yCursor = PADT + ih;
        for (const cat of D.cat_labels) {
          if (!STATE.enabled.has(cat)) continue;
          const v = D.pivot[cat]?.[origI] ?? 0;
          if (v <= 0) continue;
          const h = ih * v / top;
          const y = yCursor - h;
          parts.push(`<rect x="${PADL + slot * i + (slot - barW) / 2}" y="${y}" width="${barW}" height="${h}" fill="${couleur(cat)}" data-cat="${cat}" data-month="${F.months[i]}" data-val="${v.toFixed(2)}"/>`);
          yCursor = y;
        }
      });
      svg.innerHTML = parts.join("");
      const tt = $("#tt-stack");
      svg.querySelectorAll("rect[data-cat]").forEach(r => {
        r.addEventListener("mousemove", (e) => {
          const rect = svg.getBoundingClientRect();
          const cat = r.dataset.cat, mo = r.dataset.month, v = parseFloat(r.dataset.val);
          tt.style.display = "block";
          tt.style.left = (e.clientX - rect.left) + "px";
          tt.style.top = (e.clientY - rect.top) + "px";
          tt.innerHTML = `<strong>${mo}</strong> · ${cat} · ${EUR0(v)} EUR`;
        });
        r.addEventListener("mouseleave", () => { tt.style.display = "none"; });
      });
    }

    function drawMerchants(F) {
      const max = Math.max(1, ...F.merchants.map(m => m.total));
      const list = F.merchants.length === 0
        ? `<div class="merch-row dim">// aucun marchand : toutes catégories désactivées</div>`
        : F.merchants.map(m => {
            const w = (100 * m.total / max).toFixed(1);
            return `
              <div class="merch-row">
                <span class="merch-name" title="${m.categorie} · ${m.nb} tx">${m.nom}</span>
                <span class="merch-bar"><span class="merch-fill" style="width:${w}%; background:${couleur(m.categorie)}"></span></span>
                <span class="merch-val">${EUR0(m.total)} EUR</span>
              </div>`;
          }).join("");
      $("#merchants-list").innerHTML = list;
    }

    function renderAll() {
      const F = computeFiltered();
      $("#h-period").textContent = `${F.months[0]} → ${F.months.at(-1)}`;
      $("#h-nb").textContent = `${F.months.length} MO`;
      $("#h-total").textContent = EUR0(F.totalEnabled) + " EUR";
      $("#h-avg").textContent = EUR0(F.totalEnabled / F.months.length) + " EUR";
      const sorted = [...STATE.enabled].sort((a, b) => F.catTotals[b] - F.catTotals[a]);
      $("#h-top").textContent = sorted[0] || "—";
      const techVal = STATE.enabled.has("Tech & outils dev") ? F.catTotals["Tech & outils dev"] : 0;
      $("#h-tech").textContent = F.totalEnabled ? PCT(techVal, F.totalEnabled) + "%" : "—";

      $$(".period-btn").forEach(btn => btn.classList.toggle("active", btn.dataset.period === STATE.period));

      $$(".cat-row").forEach(row => {
        const cat = row.dataset.cat;
        const on = STATE.enabled.has(cat);
        row.classList.toggle("off", !on);
        row.querySelector(".cat-box").textContent = on ? "[x]" : "[ ]";
        const t = F.catTotals[cat] || 0;
        row.querySelector(".cat-total").textContent = EUR0(t) + " EUR";
        row.querySelector(".cat-pct").textContent = "(" + PCT(t, F.totalAll || 1) + "%)";
        row.querySelector(".cat-bar-fill").style.width = ((F.totalAll ? 100 * t / F.totalAll : 0)) + "%";
      });

      drawLine(F);
      drawStacked(F);
      drawMerchants(F);
    }

    $$(".period-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        STATE.period = btn.dataset.period;
        renderAll();
      });
    });
    document.addEventListener("keydown", (e) => {
      const map = { "1": "3", "2": "6", "3": "12", "4": "all" };
      if (map[e.key]) {
        STATE.period = map[e.key];
        renderAll();
      }
    });

    buildCatRows();
    renderAll();
  })();
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
