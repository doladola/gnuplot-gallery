"use strict";

const state = { data: null, view: "home", catId: null, subId: null, demoId: null, expandedCat: null };
const idx = { demoMap: {}, demoLoc: {} };
const GROUP_NAMES = { plots: "绘图类型", features: "画面特性", commands: "常用指令" };

const KW = "set|unset|plot|splot|replot|reset|load|save|print|show|help|exit|quit|pause|fit|call|cd|pwd|if|else|do|for|while|continue|break|function|stats|bind|test|history|refresh|reread|system|with|using|title|smooth|every|index|notitle|points|lines|linespoints|impulses|steps|boxes|filledcurves|vectors|pm3d|surface|contour|hidden3d|palette|rgb|font|key|grid|samples|style|range|label|tic|tics|border|arrow|object|term|terminal|output|size|view|mapping|isosamples|dgrid3d|xtics|ytics|ztics|xlabel|ylabel|zlabel|xrange|yrange|zrange|logscale|format|datafile|separator|multiplot|nomultiplot|colorbox|cbrange|nokey|noxtics|noytics|noztics|autoscale|angles|parametric|polar|clip";

const FUNC = "sin|cos|tan|atan|atan2|asin|acos|exp|log|log10|sqrt|abs|int|floor|ceil|real|imag|arg|besj0|besj1|besy0|besy1|rand|column|stringcolumn|value|gprintf|sprintf|word|words|strlen|substr|strstrt|sum|pi";

function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function figTitle(script) {
  const m = script.match(/set\s+title\s+["']([^"']+)["']/i);
  return m ? m[1].trim() : null;
}

function highlight(code) {
  const safe = esc(code);
  const re = new RegExp(
    "('(?:[^'\\\\]|\\\\.)*'|\"(?:[^\"\\\\]|\\\\.)*\")" +
    "|(#[^\\n]*)" +
    "|\\b(" + KW + ")\\b" +
    "|\\b(" + FUNC + ")\\b" +
    "|\\b(\\d+(?:\\.\\d+)?(?:[eE][+-]?\\d+)?)\\b",
    "gm"
  );
  return safe.replace(re, function (m, str, com, kw, fn, num) {
    if (str) return '<span class="tok-s">' + str + "</span>";
    if (com) return '<span class="tok-c">' + com + "</span>";
    if (kw) return '<span class="tok-k">' + kw + "</span>";
    if (fn) return '<span class="tok-f">' + fn + "</span>";
    if (num) return '<span class="tok-n">' + num + "</span>";
    return m;
  });
}

function groupCategories() {
  const groups = [], map = {};
  for (const c of state.data.categories) {
    const g = c.group || "plots";
    if (!map[g]) { map[g] = { id: g, name: GROUP_NAMES[g] || g, cats: [] }; groups.push(map[g]); }
    map[g].cats.push(c);
  }
  return groups;
}

async function init() {
  const content = document.getElementById("content");
  try {
    const r = await fetch("data/gallery.json");
    state.data = await r.json();
  } catch (e) {
    content.innerHTML = '<div class="loading">加载失败：未找到 data/gallery.json</div>';
    return;
  }
  for (const c of state.data.categories) {
    for (const s of c.subs) {
      for (const d of s.demos) {
        idx.demoMap[d.id] = d;
        idx.demoLoc[d.id] = { cat: c, sub: s };
      }
    }
  }
  renderNav();
  renderHome();
  document.getElementById("homeBtn").addEventListener("click", goHome);
}

function countAll() {
  let demos = 0, figs = 0;
  for (const c of state.data.categories) {
    for (const s of c.subs) {
      demos += s.demos.length;
      for (const d of s.demos) figs += d.figures.length;
    }
  }
  return { demos, figs };
}

function catCount(c) {
  let n = 0;
  for (const s of c.subs) n += s.demos.length;
  return n;
}

function catThumb(c) {
  for (const s of c.subs) {
    for (const d of s.demos) {
      if (d.figures.length) return d.figures[0].image;
    }
  }
  return null;
}

function renderNav() {
  const nav = document.getElementById("nav");
  const groups = groupCategories();
  let html = "";
  groups.forEach(function (g, gi) {
    if (gi > 0) html += '<div class="nav-divider"></div>';
    html += '<div class="nav-group-title">' + esc(g.name) + "</div>";
    g.cats.forEach(function (c) {
      const subs = c.subs.map(function (s) {
        const active = state.catId === c.id && state.subId === s.id;
        return '<li class="nav-sub' + (active ? " active" : "") + '" data-cat="' + c.id +
          '" data-sub="' + s.id + '">' + esc(s.name) +
          '<span class="nav-count">' + s.demos.length + "</span></li>";
      }).join("");
      const open = state.expandedCat === c.id;
      html += '<div class="nav-cat">' +
        '<div class="nav-cat-head' + (open ? " open" : "") + '" data-cat="' + c.id + '">' +
          '<span class="chev"></span><span class="nav-cat-name">' + esc(c.name) + "</span>" +
          '<span class="nav-count">' + catCount(c) + "</span>" +
        "</div>" +
        '<ul class="nav-subs' + (open ? "" : " hidden") + '">' + subs + "</ul>" +
      "</div>";
    });
  });
  nav.innerHTML = html;
  nav.querySelectorAll(".nav-cat-head").forEach(function (el) {
    el.addEventListener("click", function () { toggleExpand(el.dataset.cat); });
  });
  nav.querySelectorAll(".nav-sub").forEach(function (el) {
    el.addEventListener("click", function () { selectSub(el.dataset.cat, el.dataset.sub); });
  });
}

function renderHome() {
  const c = document.getElementById("content");
  const total = countAll();
  const groups = groupCategories();

  const groupSections = groups.map(function (g) {
    const cards = g.cats.map(function (cat) {
      const t = catThumb(cat);
      const img = t ? '<img src="data/' + esc(t) + '" alt="" loading="lazy">' : "";
      return '<div class="cat-card" data-cat="' + cat.id + '">' +
        '<div class="cat-card-thumb">' + img + "</div>" +
        '<div class="cat-card-body">' +
          '<div class="cat-card-name">' + esc(cat.name) + "</div>" +
          '<div class="cat-card-en">' + esc(cat.name_en) + "</div>" +
          '<div class="cat-card-count">' + catCount(cat) + " 个示例</div>" +
        "</div></div>";
    }).join("");
    return '<div class="home-group">' +
      '<div class="home-group-title"><span class="dot"></span><span>' + esc(g.name) + "</span><span class=\"line\"></span></div>" +
      '<div class="home-grid">' + cards + "</div></div>";
  }).join("");

  c.innerHTML =
    '<div class="hero">' +
      '<div class="hero-tag">GNUPLOT 6.0 · DEMO GALLERY</div>' +
      "<h1>gnuplot 绘图示例图库</h1>" +
      '<p class="hero-sub">从 gnuplot 官方演示中精选整理的绘图示例，每一张图都附带完整的绘图指令，' +
      "按图形类型与特性分类，助你快速找到想要的画法。</p>" +
      '<div class="hero-stats">' +
        '<div class="stat"><b>' + state.data.categories.length + "</b><span>图形大类</span></div>" +
        '<div class="stat"><b>' + total.demos + "</b><span>绘图示例</span></div>" +
        '<div class="stat"><b>' + total.figs + "</b><span>演示图像</span></div>" +
      "</div>" +
      '<div class="hero-author">作者：沈艺 · shenyi.box1@163.com</div>' +
    "</div>" +
    groupSections;

  c.querySelectorAll(".cat-card").forEach(function (el) {
    el.addEventListener("click", function () { selectCat(el.dataset.cat); });
  });
}

function toggleExpand(catId) {
  if (state.expandedCat === catId) {
    state.expandedCat = null;
    renderNav();
    return;
  }
  state.expandedCat = catId;
  if (state.view !== "grid" || state.catId !== catId || state.subId !== null) {
    state.view = "grid";
    state.catId = catId;
    state.subId = null;
    state.demoId = null;
    renderGrid();
    window.scrollTo(0, 0);
  }
  renderNav();
}

function selectCat(catId) {
  state.view = "grid";
  state.catId = catId;
  state.subId = null;
  state.demoId = null;
  state.expandedCat = catId;
  renderNav();
  renderGrid();
  window.scrollTo(0, 0);
}

function selectSub(catId, subId) {
  state.view = "grid";
  state.catId = catId;
  state.subId = subId;
  state.demoId = null;
  state.expandedCat = catId;
  renderNav();
  renderGrid();
  window.scrollTo(0, 0);
}

function goHome() {
  state.view = "home";
  state.catId = null;
  state.subId = null;
  state.demoId = null;
  state.expandedCat = null;
  renderNav();
  renderHome();
  window.scrollTo(0, 0);
}

function renderGrid() {
  const c = document.getElementById("content");
  const cat = state.data.categories.find(function (x) { return x.id === state.catId; });

  let html = '<div class="grid-head">' +
    '<button class="back" id="backBtn">&larr; 首页</button>' +
    "<h1>" + esc(cat.name) + "</h1>" +
    '<p class="grid-sub">' + esc(cat.name_en) + "</p></div>";

  if (state.subId) {
    const sub = cat.subs.find(function (x) { return x.id === state.subId; });
    html += '<div class="grid">' + sub.demos.map(demoCard).join("") + "</div>";
  } else {
    for (const sub of cat.subs) {
      if (!sub.demos.length) continue;
      html += '<div class="grid-section">' +
        '<h2 class="grid-sec-title">' + esc(sub.name) + "</h2>" +
        '<div class="grid">' + sub.demos.map(demoCard).join("") + "</div></div>";
    }
  }

  c.innerHTML = html;
  c.querySelectorAll(".card").forEach(function (el) {
    el.addEventListener("click", function () { openDemo(el.dataset.id); });
  });
  const back = c.querySelector("#backBtn");
  if (back) back.addEventListener("click", goHome);
}

function demoCard(d) {
  const first = d.figures[0];
  const thumb = first ? first.image : "";
  const img = thumb
    ? '<img src="data/' + esc(thumb) + '" loading="lazy" alt="">'
    : '<div class="no-img"></div>';
  return '<div class="card" data-id="' + esc(d.id) + '">' +
    '<div class="card-thumb">' + img + "</div>" +
    '<div class="card-body">' +
      '<div class="card-name">' + esc(d.name) + "</div>" +
      '<div class="card-meta">' + d.figures.length + " 张图 · " + esc(d.id) + "</div>" +
    "</div></div>";
}

function openDemo(id) {
  const loc = idx.demoLoc[id];
  if (!loc) return;
  state.view = "demo";
  state.catId = loc.cat.id;
  state.subId = loc.sub.id;
  state.demoId = id;
  state.expandedCat = loc.cat.id;
  renderNav();
  renderDemo();
  window.scrollTo(0, 0);
}

function renderDemo() {
  const c = document.getElementById("content");
  const d = idx.demoMap[state.demoId];
  const loc = idx.demoLoc[state.demoId];

  const blocks = d.figures.map(function (f, i) {
    const t = figTitle(f.script);
    const label = t ? esc(t) : "绘图指令";
    return '<div class="figure">' +
      '<div class="figure-img">' +
        '<img src="data/' + esc(f.image) + '" loading="lazy" alt="' + label + '">' +
      "</div>" +
      '<div class="figure-code">' +
        '<div class="code-bar">' +
          '<span class="code-title">' + label + "</span>" +
          '<button class="copy-btn">复制</button>' +
        "</div>" +
        '<pre class="code"><code>' + highlight(f.script) + "</code></pre>" +
      "</div></div>";
  }).join("");

  c.innerHTML =
    '<div class="detail-head">' +
      '<button class="back" id="backBtn">&larr; ' + esc(loc.sub.name) + "</button>" +
      "<h1>" + esc(d.name) + "</h1>" +
      '<p class="grid-sub">' + esc(loc.cat.name) + " · " + esc(loc.sub.name) +
      " · " + d.figures.length + " 张图 · 每图附绘图指令</p>" +
    "</div>" +
    '<div class="figures">' + blocks + "</div>";

  c.querySelector("#backBtn").addEventListener("click", function () {
    selectSub(loc.cat.id, loc.sub.id);
  });
  c.querySelectorAll(".copy-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const codeEl = btn.closest(".figure-code").querySelector("code");
      copyText(btn, codeEl.innerText);
    });
  });
}

function copyText(btn, text) {
  const done = function () {
    btn.textContent = "已复制";
    setTimeout(function () { btn.textContent = "复制"; }, 1400);
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(done).catch(function () { fallbackCopy(text, done); });
  } else {
    fallbackCopy(text, done);
  }
}

function fallbackCopy(text, done) {
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.style.position = "fixed";
  ta.style.opacity = "0";
  document.body.appendChild(ta);
  ta.select();
  try { document.execCommand("copy"); done(); } catch (e) {}
  document.body.removeChild(ta);
}

init();
