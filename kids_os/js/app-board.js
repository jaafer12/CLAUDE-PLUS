/* السبورة الذكية: رسم حر، أسطر وشبكة، وتتبّع الحروف والأرقام والأشكال مع تصحيح تلقائي. */
(function () {
  var LETTERS = [
    ['أ', 'ألف', 'أرنب', '🐰', 'rabbit'], ['ب', 'باء', 'باب', '🚪', 'door'], ['ت', 'تاء', 'تفاحة', '🍎', 'apple'], ['ث', 'ثاء', 'ثلج', '❄️', 'ice'],
    ['ج', 'جيم', 'جمل', '🐫', 'camel'], ['ح', 'حاء', 'حصان', '🐴', 'horse'], ['خ', 'خاء', 'خروف', '🐑', 'sheep'], ['د', 'دال', 'دب', '🐻', 'bear'],
    ['ذ', 'ذال', 'ذرة', '🌽', 'corn'], ['ر', 'راء', 'رمّان', '🍎', 'pomegranate'], ['ز', 'زاي', 'زهرة', '🌸', 'flower'], ['س', 'سين', 'سمكة', '🐟', 'fish'],
    ['ش', 'شين', 'شمس', '☀️', 'sun'], ['ص', 'صاد', 'صاروخ', '🚀', 'rocket'], ['ض', 'ضاد', 'ضفدع', '🐸', 'frog'], ['ط', 'طاء', 'طائرة', '✈️', 'airplane'],
    ['ظ', 'ظاء', 'ظرف', '✉️', 'envelope'], ['ع', 'عين', 'عنب', '🍇', 'grapes'], ['غ', 'غين', 'غيمة', '☁️', 'cloud'], ['ف', 'فاء', 'فيل', '🐘', 'elephant'],
    ['ق', 'قاف', 'قمر', '🌙', 'moon'], ['ك', 'كاف', 'كتاب', '📖', 'book'], ['ل', 'لام', 'ليمون', '🍋', 'lemon'], ['م', 'ميم', 'موز', '🍌', 'banana'],
    ['ن', 'نون', 'نحلة', '🐝', 'bee'], ['ه', 'هاء', 'هدية', '🎁', 'gift'], ['و', 'واو', 'وردة', '🌹', 'rose'], ['ي', 'ياء', 'يد', '✋', 'hand']
  ];
  var NUMBERS = [['٠', '0', 'صفر'], ['١', '1', 'واحد'], ['٢', '2', 'اثنان'], ['٣', '3', 'ثلاثة'], ['٤', '4', 'أربعة'],
    ['٥', '5', 'خمسة'], ['٦', '6', 'ستة'], ['٧', '7', 'سبعة'], ['٨', '8', 'ثمانية'], ['٩', '9', 'تسعة']];
  var SHAPES = [['circle', 'دائرة'], ['square', 'مربع'], ['triangle', 'مثلث'], ['rect', 'مستطيل'], ['star', 'نجمة'], ['heart', 'قلب']];
  var INK_WHITE = ['#263238', '#e53935', '#1e88e5', '#43a047', '#fb8c00', '#8e24aa', '#6d4c41', '#ec407a'];
  var INK_CHALK = ['#ffffff', '#fff176', '#f48fb1', '#81d4fa', '#a5d6a7', '#ffb74d', '#ce93d8', '#ef9a9a'];
  var SIZES = [6, 14, 28];

  var root, tools, stage, bg, dr, bctx, dctx, label, W = 0, H = 0;
  var chalk = false, color = 0, size = 1, erasing = false;
  var mode = 'free', idx = 0, strokes = [], cur = null, touchId = null;

  function list() { return mode === 'letters' ? LETTERS : mode === 'numbers' ? NUMBERS : SHAPES; }
  function tracing() { return mode === 'letters' || mode === 'numbers' || mode === 'shapes'; }
  function traced() { if (!OS.data.traced) OS.data.traced = {}; return OS.data.traced; }

  function build(body) {
    root = body;
    tools = OS.el('<div class="board-tools"></div>');
    stage = OS.el('<div class="board-wrap"><canvas></canvas><canvas></canvas><div class="trace-label hidden"></div></div>');
    body.appendChild(tools); body.appendChild(stage);
    bg = stage.childNodes[0]; dr = stage.childNodes[1]; label = stage.childNodes[2];
    bctx = bg.getContext('2d'); dctx = dr.getContext('2d');
    drawTools();
    dr.addEventListener('touchstart', down, false); dr.addEventListener('touchmove', move, false);
    dr.addEventListener('touchend', up, false); dr.addEventListener('touchcancel', up, false);
    dr.addEventListener('mousedown', down, false); dr.addEventListener('mousemove', move, false);
    window.addEventListener('mouseup', up, false);
    window.addEventListener('resize', function () { if (OS.isOpen('board')) setTimeout(resize, 300); }, false);
    return { enter: resize };
  }

  function tool(html, on, fn, cls) {
    var n = OS.el('<div class="tool' + (cls ? ' ' + cls : '') + (on ? ' on' : '') + '">' + html + '</div>');
    OS.tap(n, function () { OS.sfx('click'); fn(); });
    tools.appendChild(n); return n;
  }
  function sep() { tools.appendChild(OS.el('<div style="width:2px;height:40px;background:#cfd8dc;margin:0 8px"></div>')); }
  function br() { tools.appendChild(OS.el('<div style="width:100%;height:0"></div>')); }

  function drawTools() {
    tools.innerHTML = '';
    var inks = chalk ? INK_CHALK : INK_WHITE;
    OS.each(inks, function (c, i) {
      var n = OS.el('<div class="sw' + (!erasing && i === color ? ' on' : '') + '" style="background:' + c + '"></div>');
      OS.tap(n, function () { color = i; erasing = false; OS.sfx('click'); drawTools(); });
      tools.appendChild(n);
    });
    sep();
    OS.each(SIZES, function (s, i) {
      tool('<span class="dot" style="width:' + (s / 1.4 + 4) + 'px;height:' + (s / 1.4 + 4) + 'px"></span>', i === size, function () { size = i; drawTools(); });
    });
    sep();
    tool('ممحاة', erasing, function () { erasing = !erasing; drawTools(); }, 'txt');
    tool('↩️', false, function () { strokes.pop(); redraw(); });
    tool('❌', false, function () { strokes = []; redraw(); });
    tool(chalk ? 'سبورة بيضاء' : 'سبورة خضراء', false, function () { chalk = !chalk; color = 0; drawTools(); paintBg(); redraw(); }, 'txt');
    tool('📷', false, snapshot);
    br();
    var modes = [['free', 'رسم حر'], ['lines', 'أسطر'], ['grid', 'مربعات'], ['letters', 'حروف'], ['numbers', 'أرقام'], ['shapes', 'أشكال']];
    OS.each(modes, function (m) {
      tool(m[1], mode === m[0], function () { mode = m[0]; idx = 0; strokes = []; drawTools(); resize(); announce(); }, 'txt');
    });
    if (tracing()) {
      tool('▶', false, function () { go(-1); });
      tool('◀', false, function () { go(1); });
      tool('🔈', false, announce);
      tool('✅ تحقّق', false, check, 'txt');
    }
    if (stage) stage.style.top = tools.offsetHeight + 'px';
  }

  function go(d) { var l = list(); idx = (idx + d + l.length) % l.length; strokes = []; paintBg(); redraw(); announce(); }

  function announce() {
    if (!tracing()) return;
    var it = list()[idx];
    if (mode === 'letters') OS.say(it[1] + '. ' + it[2]);
    else if (mode === 'numbers') OS.say(it[2]);
    else OS.say(it[1]);
  }

  function resize() {
    stage.style.top = tools.offsetHeight + 'px';
    W = stage.offsetWidth; H = stage.offsetHeight;
    bg.width = dr.width = W; bg.height = dr.height = H;
    paintBg(); redraw();
  }

  // ---------- الخلفية والدليل ----------
  function glyphFont(px) { return 'bold ' + px + 'px "Geeza Pro", "Arial", sans-serif'; }

  function shapePath(c, name, cx, cy, r) {
    c.beginPath();
    if (name === 'circle') c.arc(cx, cy, r, 0, Math.PI * 2);
    else if (name === 'square') c.rect(cx - r, cy - r, 2 * r, 2 * r);
    else if (name === 'rect') c.rect(cx - r * 1.5, cy - r * 0.8, 3 * r, 1.6 * r);
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

  // يرسم شكل الدليل على أي سياق؛ s = مقياس، fat = سماحية إضافية بالبكسل
  function guide(c, s, fill, fat) {
    var it = list()[idx], cx = W * s / 2, cy = H * s / 2 + 10 * s;
    if (mode === 'shapes') {
      var r = Math.min(W, H) * s * 0.3;
      shapePath(c, it[0], cx, cy, r);
      c.lineWidth = 34 * s + (fat || 0); c.lineJoin = 'round'; c.strokeStyle = fill; c.stroke();
    } else {
      var px = Math.min(W * 0.8, H * 0.8) * s;
      c.font = glyphFont(px); c.textAlign = 'center'; c.textBaseline = 'middle';
      c.fillStyle = fill; c.fillText(it[0], cx, cy);
      if (fat) { c.lineWidth = fat; c.lineJoin = 'round'; c.strokeStyle = fill; c.strokeText(it[0], cx, cy); }
    }
  }

  function paintBg() {
    var c = bctx;
    c.fillStyle = chalk ? '#2e5d3a' : '#ffffff'; c.fillRect(0, 0, W, H);
    var line = chalk ? 'rgba(255,255,255,.25)' : '#cfd8dc';
    var i;
    if (mode === 'lines') {
      for (i = 80; i < H; i += 90) {
        c.strokeStyle = line; c.lineWidth = 2; c.beginPath(); c.moveTo(20, i); c.lineTo(W - 20, i); c.stroke();
        if (c.setLineDash) c.setLineDash([10, 10]);
        c.beginPath(); c.moveTo(20, i - 45); c.lineTo(W - 20, i - 45); c.stroke();
        if (c.setLineDash) c.setLineDash([]);
      }
    } else if (mode === 'grid') {
      c.strokeStyle = line; c.lineWidth = 1;
      for (i = 40; i < W; i += 40) { c.beginPath(); c.moveTo(i, 0); c.lineTo(i, H); c.stroke(); }
      for (i = 40; i < H; i += 40) { c.beginPath(); c.moveTo(0, i); c.lineTo(W, i); c.stroke(); }
    } else if (tracing()) {
      guide(c, 1, chalk ? 'rgba(255,255,255,.18)' : 'rgba(120,144,156,.18)');
      if (c.setLineDash) c.setLineDash([14, 12]);
      c.lineWidth = 3; c.strokeStyle = chalk ? 'rgba(255,255,255,.6)' : 'rgba(84,110,122,.6)';
      var it = list()[idx];
      if (mode === 'shapes') { shapePath(c, it[0], W / 2, H / 2 + 10, Math.min(W, H) * 0.3); c.stroke(); }
      else c.strokeText(it[0], W / 2, H / 2 + 10);
      if (c.setLineDash) c.setLineDash([]);
    }
    if (tracing()) {
      var t = list()[idx];
      label.innerHTML = mode === 'letters' ? t[0] + ' ' + t[1] + ' — ' + t[2] + ' ' + OS.pic(t[4], t[3]) :
        mode === 'numbers' ? t[0] + ' (' + t[1] + ') ' + t[2] + ' ' + dots(+t[1]) : t[1];
      label.className = 'trace-label';
    } else label.className = 'trace-label hidden';
    root.className = 'win-body' + (chalk ? ' chalk' : '');
  }
  function dots(n) { var s = ''; for (var i = 0; i < n; i++) s += '🍎'; return s; }

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
    cur = { c: (chalk ? INK_CHALK : INK_WHITE)[color], w: erasing ? 40 : SIZES[size], e: erasing, p: [p[0], p[1]] };
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
  function up(e) { if (!cur) return; if (e && e.changedTouches && !local(e)) return; cur = null; touchId = null; }

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
    if (inkN < 20) { OS.toast('✏️', 'تتبّع الخط المنقّط بإصبعك أولاً'); return; }
    var c = cov / glyph, o = out / inkN, it = list()[idx];
    if (c > 0.6 && o < 0.25) {
      OS.sfx('ding');
      var key = mode + ':' + idx, t = traced();
      if (!t[key]) { t[key] = 1; OS.addStars(1); }
      OS.toast('🌟', 'ممتاز! ' + (mode === 'letters' ? 'حرف ' + it[1] : mode === 'numbers' ? 'الرقم ' + it[2] : it[1]) + ' جميل جداً');
      groupAward();
      setTimeout(function () { if (OS.isOpen('board')) go(1); }, 2200);
    } else if (c > 0.35 && o < 0.45) {
      OS.sfx('pop'); OS.toast('👍', o >= 0.25 ? 'جيد! حاول أن تبقى على الخط' : 'جيد! أكمل تلوين الشكل كله');
    } else {
      OS.sfx('buzz'); OS.toast('🙂', 'حاول مرة أخرى، امشِ فوق النقاط');
      strokes = []; setTimeout(redraw, 600);
    }
  }
  function groupAward() {
    var t = traced(), groups = [['letters', LETTERS, 'b-letters', '🔤', 'كتبت كل الحروف!'], ['numbers', NUMBERS, 'b-numbers', '🔢', 'كتبت كل الأرقام!'], ['shapes', SHAPES, 'b-shapes', '🔷', 'رسمت كل الأشكال!']];
    var any = 0;
    for (var k in t) any++;
    if (any >= 5) OS.award('b-five', '✏️', 'تتبّعت خمسة رسوم!');
    OS.each(groups, function (g) {
      for (var i = 0; i < g[1].length; i++) if (!t[g[0] + ':' + i]) return;
      OS.award(g[2], g[3], g[4]);
    });
  }

  function snapshot() {
    var c = layer(W, H), x = c.getContext('2d');
    x.drawImage(bg, 0, 0); x.drawImage(dr, 0, 0);
    var url = c.toDataURL('image/png');
    OS.ask('<img src="' + url + '" style="width:100%;border-radius:14px;border:3px solid #cfd8dc;-webkit-touch-callout:default" ><br>اضغط مطوّلاً على الصورة واختر «حفظ الصورة»',
      [{ label: 'تمّ 👍', cls: 'btn-green' }], false);
  }

  OS.register({
    id: 'board', name: 'السبورة الذكية', icon: '✏️', color: '#3949ab', build: build,
    awards: [{ key: 'b-five', e: '✏️', l: 'خمسة رسوم' }, { key: 'b-letters', e: '🔤', l: 'كل الحروف' },
      { key: 'b-numbers', e: '🔢', l: 'كل الأرقام' }, { key: 'b-shapes', e: '🔷', l: 'كل الأشكال' }]
  });
})();
