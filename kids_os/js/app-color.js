/* التلوين: دفتر رسوم يلوّنها الطفل. يضغط على مساحة فتمتلئ باللون (الدلو)، أو يلوّن بإصبعه (الفرشاة).
   مثل السبورة: بحجم الشاشة، والأزرار تختفي ما دام يلوّن بالفرشاة. الخطوط فوق الألوان دائماً فلا تُمسح.
   الرسوم في coloring/cNN.png (رمادية)، ويضعها tools/build.py داخل الملف في OS.colorData. */
(function () {
  var COUNT = 30;
  var INKS = ['#ef4444', '#f97316', '#facc15', '#22c55e', '#38bdf8', '#a855f7', '#f472b6', '#a16207'];
  var BRUSH = 22, ERASER = 44, UNDO = 6;
  var TOP_UI = 104, BOTTOM_UI = 150, SAVE_KEY = 'nujoom_color';

  var root, paper, cv, lv, cctx, lctx, gal, top, bottom, W = 0, H = 0, PW = 0, PH = 0;
  var page = -1, color = 0, tool = 'fill', mask = null, undo = [], dirty = false, marks = 0;
  var cur = null, touchId = null, showTimer = null, imgs = {}, saved = loadSaved();

  function src(i) { return (OS.colorData && OS.colorData[i]) || 'coloring/c' + (i < 9 ? '0' : '') + (i + 1) + '.png'; }
  function colored() { return OS.data.colored || (OS.data.colored = {}); }

  // ---------- الحفظ: ألوان كل رسمة صورة PNG في مفتاح مستقل حتى لا تثقل بيانات النظام ----------
  function loadSaved() { try { return JSON.parse(localStorage.getItem(SAVE_KEY)) || {}; } catch (e) { return {}; } }
  function persist() {
    for (var tries = 0; tries < COUNT; tries++) {
      try { localStorage.setItem(SAVE_KEY, JSON.stringify(saved)); return; } catch (e) {
        // امتلأت الذاكرة: نحذف أقدم رسمة محفوظة غير الحالية ونعيد المحاولة
        var old = null;
        for (var k in saved) if (+k !== page && (old === null || saved[k].t < saved[old].t)) old = k;
        if (old === null) return;
        delete saved[old];
      }
    }
  }
  function store() {
    if (!dirty || page < 0) return;
    dirty = false;
    saved[page] = { t: +new Date(), d: cv.toDataURL('image/png') };
    persist();
  }

  function image(i, fn) {
    var im = imgs[i];
    if (im && im.complete && im.width) return fn(im);
    if (!im) { im = imgs[i] = new Image(); im.src = src(i); }
    im.addEventListener('load', function () { fn(im); }, false);
  }

  function build(body) {
    root = OS.el('<div class="bd cl"><div class="cl-paper"><canvas></canvas><canvas></canvas></div>' +
      '<div class="bd-ui bd-top"></div><div class="bd-ui bd-bottom"></div><div class="cl-gal scroll hidden"></div></div>');
    body.appendChild(root);
    paper = root.childNodes[0]; cv = paper.childNodes[0]; lv = paper.childNodes[1];
    top = root.childNodes[1]; bottom = root.childNodes[2]; gal = root.childNodes[3];
    cctx = cv.getContext('2d'); lctx = lv.getContext('2d');
    drawTop(); drawBottom();
    lv.addEventListener('touchstart', down, false); lv.addEventListener('touchmove', move, false);
    lv.addEventListener('touchend', up, false); lv.addEventListener('touchcancel', up, false);
    lv.addEventListener('mousedown', down, false); lv.addEventListener('mousemove', move, false);
    window.addEventListener('mouseup', up, false);
    window.addEventListener('resize', function () { if (OS.isOpen('color')) setTimeout(resize, 300); }, false);
    return {
      enter: function () { if (page < 0) gallery(); else resize(); },
      leave: function () { cur = null; showUI(true); store(); }
    };
  }

  // ---------- الأزرار ----------
  function button(cls, html, fn) { var n = OS.el('<div class="' + cls + '">' + html + '</div>'); OS.tap(n, fn); return n; }

  function drawTop() {
    top.innerHTML = '';
    top.appendChild(button('bd-home', OS.icon('home'), function () { OS.home(); }));
    var nav = OS.el('<div class="cl-nav"></div>');
    nav.appendChild(button('cl-round', OS.icon('back'), function () { go(-1); }));
    nav.appendChild(button('cl-round cl-all', OS.icon('grid'), gallery));
    nav.appendChild(button('cl-round cl-fwd', OS.icon('back'), function () { go(1); }));
    top.appendChild(nav);
    top.appendChild(button('cl-round cl-trash', OS.icon('trash'), clearPage));
  }

  function drawBottom() {
    bottom.innerHTML = '';
    OS.each(INKS, function (c, i) {
      bottom.appendChild(button('bd-crayon' + (tool !== 'eraser' && i === color ? ' on' : ''), OS.crayon(c), function () {
        color = i; if (tool === 'eraser') tool = 'fill'; drawBottom();
      }));
    });
    bottom.appendChild(OS.el('<div class="bd-sep"></div>'));
    var tools = [['fill', 'bucket', '#f97316', 'دلو'], ['brush', 'brush', '#3b82f6', 'فرشاة'], ['eraser', 'eraser', '#f472b6', 'ممحاة']];
    OS.each(tools, function (t) {
      bottom.appendChild(button('bd-tool' + (tool === t[0] ? ' on' : ''), '<div class="b" style="background:' + t[2] + '">' + OS.icon(t[1]) + '</div>' + t[3],
        function () { tool = t[0]; drawBottom(); }));
    });
    bottom.appendChild(button('bd-tool', '<div class="b" style="background:#94a3b8">' + OS.icon('undo') + '</div>تراجع', back));
  }

  function showUI(v) { clearTimeout(showTimer); root.className = 'bd cl' + (v ? '' : ' drawing'); }

  // ---------- معرض الرسوم ----------
  function gallery() {
    store();
    gal.innerHTML = '';
    gal.className = 'cl-gal scroll';
    var head = OS.el('<div class="cl-gal-head"></div>');
    head.appendChild(button('bd-home', OS.icon('home'), function () { OS.home(); }));
    gal.appendChild(head);
    var grid = OS.el('<div class="cl-grid"></div>'), cells = [];
    for (var i = 0; i < COUNT; i++) (function (i) {
      var n = button('cl-th' + (colored()[i] ? ' done' : ''), '<canvas width="200" height="258"></canvas><span class="ok">' + OS.icon('check') + '</span>',
        function () { openPage(i); });
      grid.appendChild(n); cells.push(n.firstChild);
    })(i);
    gal.appendChild(grid);
    gal.scrollTop = page > 2 ? cells[page].parentNode.offsetTop - 120 : 0;
    // نرسم المصغّرات واحدة واحدة حتى لا يتجمّد الآيباد
    var k = 0;
    (function next() {
      if (k >= COUNT || gal.className.indexOf('hidden') >= 0) return;
      thumb(k, cells[k], function () { k++; setTimeout(next, 15); });
    })();
  }

  function thumb(i, c, fn) {
    image(i, function (im) {
      var x = c.getContext('2d'), s = Math.min(c.width / im.width, c.height / im.height), w = im.width * s, h = im.height * s;
      x.fillStyle = '#fff'; x.fillRect(0, 0, c.width, c.height);
      function lines() {
        x.globalCompositeOperation = 'multiply'; // الخطوط فوق الألوان (إن لم يدعمها المتصفح تظهر الخطوط فقط)
        x.drawImage(im, (c.width - w) / 2, (c.height - h) / 2, w, h);
        x.globalCompositeOperation = 'source-over';
        fn();
      }
      if (!saved[i]) return lines();
      var u = new Image();
      u.onload = function () { x.drawImage(u, (c.width - w) / 2, (c.height - h) / 2, w, h); lines(); };
      u.onerror = lines;
      u.src = saved[i].d;
    });
  }

  function openPage(i) {
    store();
    page = i; undo = []; marks = 0;
    gal.className = 'cl-gal scroll hidden';
    PW = 0; resize();
  }
  function go(d) { openPage((page + d + COUNT) % COUNT); }

  // ---------- الورقة ----------
  function resize() {
    if (page < 0) return;
    W = root.offsetWidth; H = root.offsetHeight;
    var p = page;
    image(p, function (im) {
      if (p !== page) return;
      var aw = W - 24, ah = H - TOP_UI - BOTTOM_UI, s = Math.min(aw / im.width, ah / im.height);
      var w = Math.round(im.width * s), h = Math.round(im.height * s);
      var keep = null;
      if (PW && (w !== PW || h !== PH)) { keep = layer(PW, PH); keep.getContext('2d').drawImage(cv, 0, 0); }
      var fresh = !PW;
      PW = w; PH = h;
      paper.style.width = w + 'px'; paper.style.height = h + 'px';
      paper.style.left = Math.round((W - w) / 2) + 'px'; paper.style.top = Math.round(TOP_UI + (ah - h) / 2) + 'px';
      cv.width = lv.width = w; cv.height = lv.height = h;
      lines(im);
      cctx.fillStyle = '#fff'; cctx.fillRect(0, 0, w, h);
      if (keep) { cctx.drawImage(keep, 0, 0, w, h); undo = []; }
      else if (fresh && saved[p]) {
        var u = new Image();
        u.onload = function () { if (p === page) cctx.drawImage(u, 0, 0, w, h); };
        u.src = saved[p].d;
      }
    });
  }

  // الخطوط سوداء بشفافية حسب درجة الرمادي، والقناع يحدّد المساحات التي يتوقف عندها الدلو
  function lines(im) {
    lctx.clearRect(0, 0, PW, PH);
    lctx.drawImage(im, 0, 0, PW, PH);
    var d = lctx.getImageData(0, 0, PW, PH), px = d.data, n = PW * PH;
    mask = new Uint8Array(n);
    for (var i = 0, j = 0; i < n; i++, j += 4) {
      var v = px[j];
      mask[i] = v < 200 ? 1 : 0;
      px[j] = px[j + 1] = px[j + 2] = 0;
      px[j + 3] = 255 - v;
    }
    lctx.putImageData(d, 0, 0);
  }

  function layer(w, h) { var c = document.createElement('canvas'); c.width = w; c.height = h; return c; }

  function snapshot() {
    undo.push(cctx.getImageData(0, 0, PW, PH));
    if (undo.length > UNDO) undo.shift();
  }
  function back() {
    if (!undo.length) return;
    cctx.putImageData(undo.pop(), 0, 0); dirty = true;
  }
  function clearPage() {
    if (page < 0) return;
    snapshot();
    cctx.fillStyle = '#fff'; cctx.fillRect(0, 0, PW, PH); dirty = true;
  }

  // ---------- الدلو ----------
  function rgb(hex) { return [parseInt(hex.substr(1, 2), 16), parseInt(hex.substr(3, 2), 16), parseInt(hex.substr(5, 2), 16)]; }

  function fill(x, y, hex) {
    var w = PW, h = PH;
    x = Math.round(x); y = Math.round(y);
    if (x < 0 || y < 0 || x >= w || y >= h) return;
    // إن وقع الإصبع على خط نبحث عن أقرب مساحة بجانبه
    if (mask[y * w + x]) {
      var best = null;
      for (var r = 1; r <= 8 && !best; r++) {
        for (var dy = -r; dy <= r && !best; dy++) for (var dx = -r; dx <= r; dx++) {
          var xx = x + dx, yy = y + dy;
          if (xx >= 0 && yy >= 0 && xx < w && yy < h && !mask[yy * w + xx]) { best = [xx, yy]; break; }
        }
      }
      if (!best) return;
      x = best[0]; y = best[1];
    }
    var c = rgb(hex), img = cctx.getImageData(0, 0, w, h), px = img.data, seen = new Uint8Array(w * h);
    var at = (y * w + x) * 4;
    if (px[at] === c[0] && px[at + 1] === c[1] && px[at + 2] === c[2]) return;
    snapshot();
    var stack = [x, y];
    while (stack.length) {
      y = stack.pop(); x = stack.pop();
      var i = y * w + x;
      if (seen[i] || mask[i]) continue;
      while (x > 0 && !mask[i - 1] && !seen[i - 1]) { x--; i--; }
      var up = false, dn = false;
      while (x < w && !mask[i] && !seen[i]) {
        seen[i] = 1;
        if (y > 0) { if (!mask[i - w] && !seen[i - w]) { if (!up) { stack.push(x, y - 1); up = true; } } else up = false; }
        if (y < h - 1) { if (!mask[i + w] && !seen[i + w]) { if (!dn) { stack.push(x, y + 1); dn = true; } } else dn = false; }
        x++; i++;
      }
    }
    // نمدّ اللون بكسلين تحت الخط حتى لا تبقى حافة بيضاء بين اللون والخط
    for (var pass = 2; pass <= 3; pass++) {
      for (i = 0; i < w * h; i++) {
        if (seen[i] || !mask[i]) continue;
        var px0 = i % w;
        if ((px0 > 0 && seen[i - 1] && seen[i - 1] < pass) || (px0 < w - 1 && seen[i + 1] && seen[i + 1] < pass) ||
            (i >= w && seen[i - w] && seen[i - w] < pass) || (i < w * (h - 1) && seen[i + w] && seen[i + w] < pass)) seen[i] = pass;
      }
    }
    for (i = 0, at = 0; i < w * h; i++, at += 4) if (seen[i]) { px[at] = c[0]; px[at + 1] = c[1]; px[at + 2] = c[2]; px[at + 3] = 255; }
    cctx.putImageData(img, 0, 0);
    progress();
  }

  // نجمة أول مرة يلوّن فيها الطفل رسمة (خمس لمسات على الأقل)
  function progress() {
    dirty = true;
    if (++marks !== 5 || colored()[page]) return;
    colored()[page] = 1; OS.addStars(1); OS.save();
    var n = 0; for (var k in colored()) n++;
    OS.ok('رائع!', 1600);
    if (n >= 5) setTimeout(function () { OS.award('c-five', '', 'لوّنت خمس رسومات!'); }, 1700);
    if (n >= COUNT) setTimeout(function () { OS.award('c-all', '', 'لوّنت الدفتر كله!'); }, 3400);
  }

  // ---------- الفرشاة ----------
  function local(e) {
    var r = lv.getBoundingClientRect(), t = e;
    if (e.changedTouches) {
      t = null;
      for (var i = 0; i < e.changedTouches.length; i++) if (e.changedTouches[i].identifier === touchId) t = e.changedTouches[i];
      if (!t) return null;
    }
    return [t.clientX - r.left, t.clientY - r.top];
  }
  function down(e) {
    e.preventDefault();
    if (cur || !mask) return;
    if (e.changedTouches) touchId = e.changedTouches[0].identifier;
    else if (e.button) return;
    var p = local(e); if (!p) return;
    if (tool === 'fill') { touchId = null; fill(p[0], p[1], INKS[color]); return; }
    showUI(false);
    snapshot();
    cur = { c: tool === 'eraser' ? '#ffffff' : INKS[color], w: tool === 'eraser' ? ERASER : BRUSH, x: p[0], y: p[1] };
    cctx.fillStyle = cur.c; cctx.beginPath(); cctx.arc(p[0], p[1], cur.w / 2, 0, Math.PI * 2); cctx.fill();
  }
  function move(e) {
    if (!cur) return; e.preventDefault();
    var p = local(e); if (!p) return;
    cctx.strokeStyle = cur.c; cctx.lineWidth = cur.w; cctx.lineCap = cctx.lineJoin = 'round';
    cctx.beginPath(); cctx.moveTo(cur.x, cur.y); cctx.lineTo(p[0], p[1]); cctx.stroke();
    cur.x = p[0]; cur.y = p[1];
  }
  function up(e) {
    if (!cur) return;
    if (e && e.changedTouches && !local(e)) return;
    cur = null; touchId = null;
    progress();
    showTimer = setTimeout(function () { showUI(true); }, 900);
  }

  OS.register({
    id: 'color', name: 'التلوين', icon: 'palette', color: '#f97316', shade: '#c2410c', build: build, full: true,
    awards: [{ key: 'c-five', e: '', l: 'خمس رسومات' }, { key: 'c-all', e: '', l: 'الدفتر كله' }]
  });
})();
