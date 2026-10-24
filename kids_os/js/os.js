/* نجوم — نواة النظام: الإقلاع، الشاشة الرئيسية، النوافذ، النجوم، الرسائل. النظام صامت تماماً.
   مكتوب بـ ES5 فقط (بلا let/const/=>) ليعمل على Safari 9 في iOS 9.3.5. */
var OS = (function () {
  var KEY = 'nujoom_v1';
  var data = { name: '', stars: 0, awards: {}, wallpaper: 'wp-sky', opened: {} };
  var apps = [], appById = {}, current = null;

  function $(id) { return document.getElementById(id); }
  function el(html) { var d = document.createElement('div'); d.innerHTML = html; return d.firstChild; }
  function each(list, fn) { for (var i = 0; i < list.length; i++) fn(list[i], i); }
  function shuffle(a) { a = a.slice(); for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; } return a; }
  function strip(html) { return String(html).replace(/<[^>]+>/g, ' '); }

  // ---------- التخزين (يفشل بصمت في التصفح الخاص) ----------
  function load() {
    try { var s = localStorage.getItem(KEY); if (s) { var d = JSON.parse(s); for (var k in d) data[k] = d[k]; } } catch (e) {}
  }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(data)); } catch (e) {} }

  // ---------- اللمس السريع (بدون تأخير 300ms) ----------
  var lastTouch = 0;
  function tap(node, fn) {
    var sx = 0, sy = 0, moved = false;
    node.addEventListener('touchstart', function (e) { var p = e.touches[0]; sx = p.clientX; sy = p.clientY; moved = false; }, false);
    node.addEventListener('touchmove', function (e) { var p = e.touches[0]; if (Math.abs(p.clientX - sx) > 12 || Math.abs(p.clientY - sy) > 12) moved = true; }, false);
    node.addEventListener('touchend', function (e) { if (moved) return; lastTouch = Date.now(); e.preventDefault(); fn.call(node, e); }, false);
    node.addEventListener('click', function (e) { if (Date.now() - lastTouch < 800) return; fn.call(node, e); }, false);
    return node;
  }
  // يحوّل الإحداثيات من لمس أو فأرة
  function point(e) { var t = e.changedTouches ? e.changedTouches[0] : e; return { x: t.clientX, y: t.clientY }; }
  // يحوّل لمسة إلى إحداثيات داخل لوحة رسم مهما كان حجمها المعروض
  function canvasPoint(cv, e) {
    var r = cv.getBoundingClientRect(), p = point(e);
    return { x: (p.x - r.left) * cv.width / r.width, y: (p.y - r.top) * cv.height / r.height };
  }

  // ---------- الصور الحقيقية ----------
  // في النسخة المجمّعة تكون الصور داخل الملف نفسه (api.photoData)، وإلا تُقرأ من مجلد img
  function photoUrl(id) { return (api.photoData && api.photoData[id]) || 'img/' + id + '.jpg'; }
  function pic(id, fallback, cls) {
    return id && api.photos[id] ? '<img class="pic' + (cls ? ' ' + cls : '') + '" src="' + photoUrl(id) + '" alt="">' : fallback;
  }
  // صورة جاهزة للرسم على لوحة، أو null إن لم توجد
  var imgCache = {};
  function photo(id) {
    if (!api.photos[id]) return null;
    if (!imgCache[id]) { imgCache[id] = new Image(); imgCache[id].src = photoUrl(id); }
    return imgCache[id].complete && imgCache[id].naturalWidth ? imgCache[id] : null;
  }

  // ---------- النجوم والملصقات ----------
  function refreshStars() { var b = $('sbStars'); if (b) b.innerHTML = data.stars; }
  function addStars(n) { data.stars += n; save(); refreshStars(); }
  // يمنح ملصقاً مرة واحدة فقط مع نجمة؛ يرجع true إذا كان جديداً
  function award(key, emoji, text) {
    if (data.awards[key]) return false;
    data.awards[key] = Date.now();
    addStars(1);
    show('star', 'star', (text || 'أحسنت!') + ' — ربحت نجمة', 2800);
    return true;
  }

  // ---------- الرسائل ----------
  var toastTimer = null;
  function show(kind, icon, text, ms) {
    var t = $('toast');
    t.innerHTML = '<div class="toast-icon">' + api.icon(icon) + '</div><div class="toast-text">' + text + '</div>';
    t.className = 'hidden'; void t.offsetWidth; t.className = kind;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.className = 'hidden'; }, ms || 2200);
  }
  function ok(text, ms) { show('ok', 'check', text, ms); }      // جواب صحيح
  function hint(text, ms) { show('hint', 'eye', text, ms); }    // انظر وحاول مرة أخرى

  // يعرض سؤالاً بأزرار: buttons = [{label, cls, fn}]
  function ask(html, buttons) {
    var box = $('modalBtns'); box.innerHTML = '';
    $('modalText').innerHTML = html;
    each(buttons, function (b) {
      var n = el('<button class="btn ' + (b.cls || 'btn-white') + '">' + b.label + '</button>');
      tap(n, function () { $('modal').className = 'hidden'; if (b.fn) b.fn(); });
      box.appendChild(n);
    });
    $('modal').className = '';
  }

  // صندوق شرح قصير أعلى التجربة
  function info(html) {
    var n = el('<div class="info">' + html + '</div>');
    n.set = function (h) { n.innerHTML = h; };
    return n;
  }

  // ---------- التاريخ والترحيب ----------
  var DAYS = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت'];
  var MONTHS = ['كانون الثاني', 'شباط', 'آذار', 'نيسان', 'أيار', 'حزيران', 'تموز', 'آب', 'أيلول', 'تشرين الأول', 'تشرين الثاني', 'كانون الأول'];
  function greet() {
    var d = new Date();
    $('hello').innerHTML = (d.getHours() < 12 ? 'صباح الخير' : 'مساء الخير') + (data.name ? ' يا ' + data.name : '');
    $('date').innerHTML = DAYS[d.getDay()] + ' ' + d.getDate() + ' ' + MONTHS[d.getMonth()];
  }

  // ---------- التطبيقات والنوافذ ----------
  // app = { id, name, icon, color, shade, build(body, app) → {enter, leave}, awards, scroll, dock }
  function register(app) { apps.push(app); appById[app.id] = app; }

  function drawHome() {
    var grid = $('grid'); grid.innerHTML = '';
    each(apps, function (a) {
      if (a.dock) return; // النجوم والإعدادات في الشريط العلوي
      var left = countLeft(a);
      var n = el('<div class="card" style="background:' + a.color + ';box-shadow:0 6px 0 ' + a.shade + '">' +
        (left ? '<span class="badge">' + left + '</span>' : '') +
        '<div class="tile">' + api.icon(a.icon) + '</div><div class="nm">' + a.name + '</div></div>');
      tap(n, function () { open(a.id); });
      grid.appendChild(n);
    });
    greet(); refreshStars();
  }
  function countLeft(a) { var c = 0; each(a.awards || [], function (w) { if (!data.awards[w.key]) c++; }); return c; }

  function open(id) {
    var a = appById[id]; if (!a) return;
    if (current) closeWin(true);
    if (!a.win) {
      a.win = el('<div class="win closed"><div class="win-head" style="background:' + a.color + '">' +
        '<button class="back">' + api.icon('back') + 'الرئيسية</button>' +
        '<div class="win-title"><div class="t" style="color:' + a.color + '">' + api.icon(a.icon) + '</div>' + a.name + '</div>' +
        '<div class="win-extra"></div></div>' +
        '<div class="win-body' + (a.scroll ? ' scroll' : '') + '"></div></div>');
      $('windows').appendChild(a.win);
      tap(a.win.querySelector('.back'), function () { home(); });
      a.body = a.win.lastChild; a.extra = a.win.querySelector('.win-extra');
      a.ctl = a.build(a.body, a) || {};
    }
    a.win.style.display = '';
    void a.win.offsetWidth;
    a.win.className = 'win';
    current = a;
    data.opened[id] = (data.opened[id] || 0) + 1; save();
    setTimeout(function () { if (current === a && a.ctl.enter) a.ctl.enter(); }, 260);
  }
  function closeWin(instant) {
    var a = current; if (!a) return;
    current = null;
    if (a.ctl.leave) a.ctl.leave();
    $('modal').className = 'hidden';
    a.win.className = 'win closed';
    if (instant) a.win.style.display = 'none';
    else setTimeout(function () { if (current !== a) a.win.style.display = 'none'; }, 280);
  }
  function home() { if (!current) return; closeWin(false); drawHome(); }

  function setWallpaper(w) { data.wallpaper = w; save(); $('desk').className = w; }

  // يمنع تمرير الصفحة ومطّها إلا داخل العناصر القابلة للتمرير
  function blockBounce() {
    document.addEventListener('touchmove', function (e) {
      var n = e.target;
      while (n && n !== document.body) {
        if (n.id === 'home') return;
        if (n.className && typeof n.className === 'string' && n.className.indexOf('scroll') >= 0) return;
        if (n.tagName === 'INPUT') return;
        n = n.parentNode;
      }
      e.preventDefault();
    }, false);
  }

  function start() {
    load();
    blockBounce();
    $('starIcon').innerHTML = api.icon('star');
    $('gearIcon').innerHTML = api.icon('gear');
    $('bootLogo').innerHTML = api.icon('star');
    tap($('starChip'), function () { open('stars'); });
    tap($('gearChip'), function () { open('settings'); });
    setWallpaper(data.wallpaper);
    drawHome();
    setInterval(greet, 60000);

    // تحديث النسخة المخزّنة بلا إنترنت عند توفر نسخة أحدث
    try {
      var ac = window.applicationCache;
      if (ac) ac.addEventListener('updateready', function () { try { ac.swapCache(); } catch (e) {} location.reload(); }, false);
    } catch (e) {}

    var p = 0, fill = $('bootFill');
    var iv = setInterval(function () {
      p += 14; fill.style.width = Math.min(p, 100) + '%';
      if (p >= 112) { clearInterval(iv); $('boot').className = 'hidden'; }
    }, 110);
  }

  var api = {
    start: start, pic: pic, photo: photo, photoUrl: photoUrl, photos: {}, photoData: null,
    canvasPoint: canvasPoint, register: register, open: open, home: home,
    tap: tap, point: point, el: el, each: each, shuffle: shuffle, strip: strip, $: $,
    ok: ok, hint: hint, ask: ask, info: info,
    award: award, addStars: addStars, refreshStars: refreshStars,
    data: data, save: save, apps: apps, setWallpaper: setWallpaper,
    isOpen: function (id) { return current && current.id === id; }
  };
  return api;
})();
