/* السبورة الذكية: لوحة بحجم الشاشة كلها. الأزرار تطفو فوقها وتختفي ما دام الطفل يرسم،
   وتعود بعد أن يرفع إصبعه. رسم حر، أو تتبّع الأشكال والأرقام والحروف مع تصحيح تلقائي. */
(function () {
  var LETTERS = [
    ['أ', 'ألف', 'أرنب', 'rabbit'], ['ب', 'باء', 'باب', 'door'], ['ت', 'تاء', 'تفاحة', 'apple'], ['ث', 'ثاء', 'ثلج', 'ice'],
    ['ج', 'جيم', 'جمل', 'camel'], ['ح', 'حاء', 'حصان', 'horse'], ['خ', 'خاء', 'خروف', 'sheep'], ['د', 'دال', 'دب', 'bear'],
    ['ذ', 'ذال', 'ذرة', 'corn'], ['ر', 'راء', 'رمّان', 'pomegranate'], ['ز', 'زاي', 'زهرة', 'flower'], ['س', 'سين', 'سمكة', 'fish'],
    ['ش', 'شين', 'شمس', 'sun'], ['ص', 'صاد', 'صاروخ', 'rocket'], ['ض', 'ضاد', 'ضفدع', 'frog'], ['ط', 'طاء', 'طائرة', 'airplane'],
    ['ظ', 'ظاء', 'ظرف', 'envelope'], ['ع', 'عين', 'عنب', 'grapes'], ['غ', 'غين', 'غيمة', 'cloud'], ['ف', 'فاء', 'فيل', 'elephant'],
    ['ق', 'قاف', 'قمر', 'moon'], ['ك', 'كاف', 'كتاب', 'book'], ['ل', 'لام', 'ليمون', 'lemon'], ['م', 'ميم', 'موز', 'banana'],
    ['ن', 'نون', 'نحلة', 'bee'], ['ه', 'هاء', 'هدية', 'gift'], ['و', 'واو', 'وردة', 'rose'], ['ي', 'ياء', 'يد', 'hand']
  ];
  var NUMBERS = [['١', 'واحد'], ['٢', 'اثنان'], ['٣', 'ثلاثة'], ['٤', 'أربعة'], ['٥', 'خمسة'],
    ['٦', 'ستة'], ['٧', 'سبعة'], ['٨', 'ثمانية'], ['٩', 'تسعة'], ['٠', 'صفر']];
  var SHAPES = [['circle', 'دائرة'], ['square', 'مربع'], ['triangle', 'مثلث'], ['star', 'نجمة'], ['heart', 'قلب'], ['rect', 'مستطيل']];
  var INKS = ['#1f2937', '#ef4444', '#f59e0b', '#22c55e', '#3b82f6', '#a855f7'];
  var PEN = 18, ERASER = 56;
  var TOP_UI = 130, BOTTOM_UI = 170; // المساحة التي تغطيها الأزرار حين تظهر

  var root, bg, dr, bctx, dctx, top, bottom, trace, W = 0, H = 0;
  var color = 0, erasing = false, mode = 'free', idx = 0, strokes = [], cur = null, touchId = null, showTimer = null;

  function list() { return mode === 'letters' ? LETTERS : mode === 'numbers' ? NUMBERS : SHAPES; }
  function tracing() { return mode !== 'free'; }
  function traced() { return OS.data.traced || (OS.data.traced = {}); }

  function build(body) {
    root = OS.el('<div class="bd"><canvas></canvas><canvas></canvas>' +
      '<div class="bd-ui bd-top"></div><div class="bd-ui bd-trace"></div><div class="bd-ui bd-bottom"></div></div>');
    body.appendChild(root);
    bg = root.childNodes[0]; dr = root.childNodes[1];
    top = root.childNodes[2]; trace = root.childNodes[3]; bottom = root.childNodes[4];
    bctx = bg.getContext('2d'); dctx = dr.getContext('2d');
    drawTop(); drawBottom();
    dr.addEventListener('touchstart', down, false); dr.addEventListener('touchmove', move, false);
    dr.addEventListener('touchend', up, false); dr.addEventListener('touchcancel', up, false);
    dr.addEventListener('mousedown', down, false); dr.addEventListener('mousemove', move, false);
    window.addEventListener('mouseup', up, false);
    window.addEventListener('resize', function () { if (OS.isOpen('board')) setTimeout(resize, 300); }, false);
    return { enter: resize, leave: function () { cur = null; showUI(true); } };
  }

  // ---------- الأزرار العائمة ----------
  function button(cls, html, fn) {
    var n = OS.el('<div class="' + cls + '">' + html + '</div>');
    OS.tap(n, fn);
    return n;
  }

  function drawTop() {
    top.innerHTML = '';
    top.appendChild(button('bd-home', OS.icon('home'), function () { OS.home(); }));
    var tabs = OS.el('<div class="bd-tabs"></div>');
    var modes = [['free', OS.icon('pencil'), 'ارسم'], ['shapes', OS.icon('shapes'), 'أشكال'], ['numbers', '<b>١٢٣</b>', 'أرقام'], ['letters', '<b>أ ب ت</b>', 'حروف']];
    OS.each(modes, function (m) {
      tabs.appendChild(button('bd-tab' + (mode === m[0] ? ' on' : ''), '<div class="tp">' + m[1] + '</div>' + m[2], function () {
        mode = m[0]; idx = 0; strokes = []; drawTop(); paintBg(); redraw();
      }));
    });
    top.appendChild(tabs);
  }

  // قلم تلوين مرسوم: رأس مدبّب وجسم بلون الحبر
  function crayon(c) {
    return '<svg viewBox="0 0 40 100" width="46" height="112"><path d="M8 36 L20 4 L32 36 Z" fill="' + c + '"/>' +
      '<rect x="6" y="34" width="28" height="64" rx="8" fill="' + c + '"/><rect x="6" y="72" width="28" height="9" fill="#fff" opacity=".45"/></svg>';
  }
  function drawBottom() {
    bottom.innerHTML = '';
    OS.each(INKS, function (c, i) {
      bottom.appendChild(button('bd-crayon' + (!erasing && i === color ? ' on' : ''), crayon(c), function () { color = i; erasing = false; drawBottom(); }));
    });
    bottom.appendChild(OS.el('<div class="bd-sep"></div>'));
    var tools = [['eraser', '#f472b6', 'ممحاة', function () { erasing = !erasing; drawBottom(); }],
      ['undo', '#94a3b8', 'تراجع', function () { strokes.pop(); redraw(); }],
      ['trash', '#ef4444', 'امسح', function () { strokes = []; redraw(); }]];
    OS.each(tools, function (t) {
      bottom.appendChild(button('bd-tool' + (t[0] === 'eraser' && erasing ? ' on' : ''),
        '<div class="b" style="background:' + t[1] + '">' + OS.icon(t[0]) + '</div>' + t[2], t[3]));
    });
  }

  function drawTrace() {
    trace.innerHTML = '';
    if (!tracing()) return;
    var it = list()[idx], l = list();
    var card = mode === 'letters' ? OS.pic(it[3], '') + '<div><div class="l">' + it[0] + '</div><div class="w">' + it[2] + '</div></div>'
      : mode === 'numbers' ? '<div><div class="l">' + it[0] + '</div><div class="w">' + it[1] + '</div></div>'
      : '<div><div class="w">' + it[1] + '</div></div>';
    trace.appendChild(OS.el('<div class="bd-card">' + card + '</div>'));
    var d = '<div class="bd-dots">';
    for (var i = 0; i < l.length; i++) d += '<span' + (traced()[mode + ':' + i] ? ' class="done"' : '') + (i === idx ? ' style="background:#6366f1"' : '') + '></span>';
    trace.appendChild(OS.el(d + '</div>'));
    trace.appendChild(button('bd-arrow bd-prev', OS.icon('back'), function () { go(-1); }));
    trace.appendChild(button('bd-arrow bd-next', OS.icon('back'), function () { go(1); }));
    trace.appendChild(button('bd-check', OS.icon('check'), check));
  }

  function go(d) { var l = list(); idx = (idx + d + l.length) % l.length; strokes = []; paintBg(); redraw(); }

  // تختفي الأزرار ما دام الإصبع على اللوحة، وتعود بعد لحظة من رفعه
  function showUI(v) {
    clearTimeout(showTimer);
    root.className = 'bd' + (v ? '' : ' drawing');
  }

  function resize() {
    W = root.offsetWidth; H = root.offsetHeight;
    bg.width = dr.width = W; bg.height = dr.height = H;
    paintBg(); redraw();
  }

  // ---------- الدليل ----------
  function glyphFont(px) { return 'bold ' + px + 'px "Geeza Pro", "Arial", sans-serif'; }

  function shapePath(c, name, cx, cy, r) {
    c.beginPath();
    if (name === 'circle') c.arc(cx, cy, r, 0, Math.PI * 2);
    else if (name === 'square') c.rect(cx - r, cy - r, 2 * r, 2 * r);
    else if (name === 'rect') c.rect(cx - r * 1.4, cy - r * 0.8, 2.8 * r, 1.6 * r);
    else if (name === 'triangle') { c.moveTo(cx, cy - r); c.lineTo(cx + r * 1.1, cy + r * 0.8); c.lineTo(cx - r * 1.1, cy + r * 0.8); c.closePath(); }
    else if (name === 'star') {
      for (var i = 0; i < 10; i++) {
        var a = -Math.PI / 2 + i * Math.PI / 5, rr = i % 2 ? r * 0.45 : r;
        if (i) c.lineTo(cx + rr * Math.cos(a), cy + rr * Math.sin(a)); else c.moveTo(cx + rr * Math.cos(a), cy + rr * Math.sin(a));
      }
      c.closePath();
    } else if (name === 'heart') {
      c.moveTo(cx, cy + r * 0.9);
      c.bezierCurveTo(cx - r * 1.6, cy - r * 0.1, cx - r * 0.7, cy - r * 1.3, cx, cy - r * 0.45);
      c.bezierCurveTo(cx + r * 0.7, cy - r * 1.3, cx + r * 1.6, cy - r * 0.1, cx, cy + r * 0.9);
      c.closePath();
    }
  }

  // حدود الحرف الفعلية بالبكسل (تختلف من خط لآخر)، تُحسب مرة لكل حرف
  var boxes = {};
  function glyphBox(ch) {
    if (boxes[ch]) return boxes[ch];
    var cv = layer(600, 600), x = cv.getContext('2d');
    x.font = glyphFont(400); x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillStyle = '#000';
    x.fillText(ch, 300, 300);
    var d = x.getImageData(0, 0, 600, 600).data, x0 = 600, y0 = 600, x1 = 0, y1 = 0;
    for (var y = 0; y < 600; y++) for (var i = 0; i < 600; i++) {
      if (d[(y * 600 + i) * 4 + 3] > 40) { if (i < x0) x0 = i; if (i > x1) x1 = i; if (y < y0) y0 = y; if (y > y1) y1 = y; }
    }
    if (x1 < x0) { x0 = y0 = 100; x1 = y1 = 500; }
    return (boxes[ch] = { cx: (x0 + x1) / 2, cy: (y0 + y1) / 2, w: x1 - x0 + 1, h: y1 - y0 + 1 });
  }

  // يرسم الدليل في المساحة بين الأزرار العلوية والسفلية؛ s = مقياس، fat = سماحية، outline = لون الحدّ
  function guide(c, s, fill, fat, outline) {
    var it = list()[idx], aw = W * s, ah = (H - TOP_UI - BOTTOM_UI) * s, cx = aw / 2, cy = TOP_UI * s + ah / 2;
    if (mode === 'shapes') {
      var r = Math.min(aw * 0.32, ah * 0.4);
      shapePath(c, it[0], cx, cy, r);
      c.lineWidth = 46 * s + (fat || 0); c.lineJoin = 'round'; c.strokeStyle = fill; c.stroke();
      if (outline) {
        if (c.setLineDash) c.setLineDash([16, 14]);
        c.lineWidth = 4 * s; c.strokeStyle = outline; c.stroke();
        if (c.setLineDash) c.setLineDash([]);
      }
      return;
    }
    // نكبّر الحرف ليملأ المساحة مهما كان الخط، مع حدّ أعلى للحروف الصغيرة مثل ٠
    var b = glyphBox(it[0]), base = Math.min(aw, ah) * 0.85 / 400;
    var k = Math.min(aw * 0.8 / b.w, ah * 0.9 / b.h, base * 1.6);
    c.save();
    c.translate(cx, cy); c.scale(k, k); c.translate(-b.cx, -b.cy);
    c.font = glyphFont(400); c.textAlign = 'center'; c.textBaseline = 'middle';
    c.fillStyle = fill; c.fillText(it[0], 300, 300);
    c.lineJoin = 'round';
    if (fat) { c.lineWidth = fat / k; c.strokeStyle = fill; c.strokeText(it[0], 300, 300); }
    if (outline) { c.lineWidth = 4 / k; c.strokeStyle = outline; c.strokeText(it[0], 300, 300); }
    c.restore();
  }

  function paintBg() {
    bctx.fillStyle = '#ffffff'; bctx.fillRect(0, 0, W, H);
    if (tracing()) guide(bctx, 1, '#eef0fb', 0, '#c7cbf2');
    drawTrace();
  }

  // ---------- الرسم ----------
  function local(e) {
    var r = dr.getBoundingClientRect(), t = e;
    if (e.changedTouches) {
      t = null;
      for (var i = 0; i < e.changedTouches.length; i++) if (e.changedTouches[i].identifier === touchId) t = e.changedTouches[i];
      if (!t) return null;
    }
    return [t.clientX - r.left, t.clientY - r.top];
  }
  function down(e) {
    e.preventDefault();
    if (cur) return;
    if (e.changedTouches) touchId = e.changedTouches[0].identifier;
    else if (e.button) return;
    var p = local(e); if (!p) return;
    showUI(false);
    cur = { c: INKS[color], w: erasing ? ERASER : PEN, e: erasing, p: [p[0], p[1]] };
    strokes.push(cur);
    dot(dctx, cur, p[0], p[1], 1);
  }
  function move(e) {
    if (!cur) return; e.preventDefault();
    var p = local(e); if (!p) return;
    var pts = cur.p, n = pts.length;
    seg(dctx, cur, pts[n - 2], pts[n - 1], p[0], p[1], 1);
    pts.push(p[0], p[1]);
  }
  function up(e) {
    if (!cur) return;
    if (e && e.changedTouches && !local(e)) return;
    cur = null; touchId = null;
    showTimer = setTimeout(function () { showUI(true); }, 900);
  }

  function style(c, s, sc, minW) {
    c.globalCompositeOperation = s.e ? 'destination-out' : 'source-over';
    c.strokeStyle = c.fillStyle = s.c; c.lineCap = 'round'; c.lineJoin = 'round';
    c.lineWidth = Math.max(s.w, minW || 0) * sc;
  }
  function dot(c, s, x, y, sc, minW) { style(c, s, sc, minW); c.beginPath(); c.arc(x * sc, y * sc, c.lineWidth / 2, 0, Math.PI * 2); c.fill(); }
  function seg(c, s, x1, y1, x2, y2, sc, minW) { style(c, s, sc, minW); c.beginPath(); c.moveTo(x1 * sc, y1 * sc); c.lineTo(x2 * sc, y2 * sc); c.stroke(); }
  function paintStrokes(c, sc, minW) {
    OS.each(strokes, function (s) {
      var p = s.p;
      dot(c, s, p[0], p[1], sc, minW);
      for (var i = 2; i < p.length; i += 2) seg(c, s, p[i - 2], p[i - 1], p[i], p[i + 1], sc, minW);
    });
    c.globalCompositeOperation = 'source-over';
  }
  function redraw() { dctx.clearRect(0, 0, W, H); paintStrokes(dctx, 1); }

  // ---------- التصحيح الذكي ----------
  function layer(w, h) { var c = document.createElement('canvas'); c.width = w; c.height = h; return c; }
  function check() {
    var s = 0.25, w = Math.round(W * s), h = Math.round(H * s);
    var m = layer(w, h), near = layer(w, h), ink = layer(w, h);
    guide(m.getContext('2d'), s, '#000');
    guide(near.getContext('2d'), s, '#000', 70 * s);
    paintStrokes(ink.getContext('2d'), s, 34);
    var a = m.getContext('2d').getImageData(0, 0, w, h).data,
        b = near.getContext('2d').getImageData(0, 0, w, h).data,
        k = ink.getContext('2d').getImageData(0, 0, w, h).data;
    var glyph = 0, cov = 0, inkN = 0, out = 0;
    for (var i = 3; i < a.length; i += 4) {
      var g = a[i] > 60, n = b[i] > 60, d = k[i] > 60;
      if (g) { glyph++; if (d) cov++; }
      if (d) { inkN++; if (!n) out++; }
    }
    if (inkN < 20) { OS.hint('امشِ بإصبعك فوق الشكل'); return; }
    var c = cov / glyph, o = out / inkN;
    if (c > 0.55 && o < 0.3) {
      var key = mode + ':' + idx, t = traced();
      if (!t[key]) { t[key] = 1; OS.addStars(1); OS.save(); }
      OS.ok('ممتاز!');
      groupAward();
      setTimeout(function () { if (OS.isOpen('board')) go(1); }, 1800);
    } else if (c > 0.3 && o < 0.5) {
      OS.ok('جيد! أكمل الشكل كله');
    } else {
      OS.hint('حاول مرة أخرى');
      strokes = []; setTimeout(redraw, 600);
    }
  }
  function groupAward() {
    var t = traced(), groups = [['letters', LETTERS, 'b-letters', 'كتبت كل الحروف!'], ['numbers', NUMBERS, 'b-numbers', 'كتبت كل الأرقام!'], ['shapes', SHAPES, 'b-shapes', 'رسمت كل الأشكال!']];
    var any = 0;
    for (var k in t) any++;
    if (any >= 5) OS.award('b-five', '', 'تتبّعت خمسة رسوم!');
    OS.each(groups, function (g) {
      for (var i = 0; i < g[1].length; i++) if (!t[g[0] + ':' + i]) return;
      OS.award(g[2], '', g[3]);
    });
  }

  OS.register({
    id: 'board', name: 'السبورة الذكية', icon: 'pencil', color: '#6366f1', shade: '#4338ca', build: build, full: true,
    awards: [{ key: 'b-five', e: '', l: 'خمسة رسوم' }, { key: 'b-letters', e: '', l: 'كل الحروف' },
      { key: 'b-numbers', e: '', l: 'كل الأرقام' }, { key: 'b-shapes', e: '', l: 'كل الأشكال' }]
  });
})();
