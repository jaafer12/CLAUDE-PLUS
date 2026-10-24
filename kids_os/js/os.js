/* نجوم — نواة النظام: الإقلاع، القفل، الشاشة الرئيسية، النوافذ، النجوم، الصوت، النطق.
   مكتوب بـ ES5 فقط (بلا let/const/=>) ليعمل على Safari 9 في iOS 9.3.5. */
var OS = (function () {
  var KEY = 'nujoom_v1';
  var data = { name: '', stars: 0, awards: {}, wallpaper: 'wp-sky', sound: true, opened: {} };
  var apps = [], appById = {}, current = null;

  function $(id) { return document.getElementById(id); }
  function el(html) { var d = document.createElement('div'); d.innerHTML = html; return d.firstChild; }
  function each(list, fn) { for (var i = 0; i < list.length; i++) fn(list[i], i); }
  function shuffle(a) { a = a.slice(); for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; } return a; }

  // ---------- التخزين (يفشل بصمت في التصفح الخاص) ----------
  function load() {
    try { var s = localStorage.getItem(KEY); if (s) { var d = JSON.parse(s); for (var k in d) data[k] = d[k]; } } catch (e) {}
  }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(data)); } catch (e) {} }

  // ---------- اللمس السريع (بدون تأخير 300ms) ----------
  var lastTouch = 0;
  function tap(node, fn) {
    var sx = 0, sy = 0, moved = false;
    node.addEventListener('touchstart', function (e) { var p = e.touches[0]; sx = p.clientX; sy = p.clientY; moved = false; unlockAudio(); }, false);
    node.addEventListener('touchmove', function (e) { var p = e.touches[0]; if (Math.abs(p.clientX - sx) > 12 || Math.abs(p.clientY - sy) > 12) moved = true; }, false);
    node.addEventListener('touchend', function (e) { if (moved) return; lastTouch = Date.now(); e.preventDefault(); fn.call(node, e); }, false);
    node.addEventListener('click', function (e) { if (Date.now() - lastTouch < 800) return; fn.call(node, e); }, false);
    return node;
  }
  // يحوّل الإحداثيات من لمس أو فأرة
  function point(e) { var t = e.changedTouches ? e.changedTouches[0] : e; return { x: t.clientX, y: t.clientY }; }

  // ---------- الأصوات المولّدة ----------
  var actx = null;
  function unlockAudio() {
    if (actx) { if (actx.state === 'suspended' && actx.resume) actx.resume(); return; }
    var AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    try {
      actx = new AC();
      var b = actx.createBuffer(1, 1, 22050), s = actx.createBufferSource();
      s.buffer = b; s.connect(actx.destination); (s.start ? s.start(0) : s.noteOn(0));
    } catch (e) { actx = null; }
  }
  function tone(freq, start, dur, type, vol) {
    if (!actx || !data.sound) return;
    var o = actx.createOscillator(), g = (actx.createGain || actx.createGainNode).call(actx);
    var t = actx.currentTime + start;
    o.type = type || 'sine'; o.frequency.value = freq;
    g.gain.setValueAtTime(vol || 0.25, t);
    g.gain.exponentialRampToValueAtTime(0.001, t + dur);
    o.connect(g); g.connect(actx.destination);
    (o.start ? o.start(t) : o.noteOn(t)); (o.stop ? o.stop(t + dur + 0.05) : o.noteOff(t + dur + 0.05));
  }
  var SFX = {
    click: function () { tone(880, 0, 0.06, 'square', 0.08); },
    pop: function () { tone(520, 0, 0.1, 'sine', 0.3); tone(780, 0.05, 0.12, 'sine', 0.2); },
    ding: function () { tone(660, 0, 0.18); tone(880, 0.14, 0.18); tone(1320, 0.28, 0.35); },
    buzz: function () { tone(160, 0, 0.3, 'sawtooth', 0.15); },
    open: function () { tone(400, 0, 0.12, 'sine', 0.15); tone(600, 0.06, 0.15, 'sine', 0.15); },
    close: function () { tone(600, 0, 0.12, 'sine', 0.15); tone(400, 0.06, 0.15, 'sine', 0.15); },
    splash: function () { for (var i = 0; i < 6; i++) tone(300 + Math.random() * 900, i * 0.03, 0.12, 'triangle', 0.08); },
    win: function () { var n = [523, 659, 784, 1047]; for (var i = 0; i < n.length; i++) tone(n[i], i * 0.12, 0.25, 'triangle', 0.25); }
  };
  function sfx(name) { unlockAudio(); if (SFX[name]) SFX[name](); }
  // نغمة موسيقية (للإكسيليفون)
  function note(freq, dur) { unlockAudio(); tone(freq, 0, dur || 0.8, 'triangle', 0.35); tone(freq * 2, 0, (dur || 0.8) / 2, 'sine', 0.08); }

  // يحوّل لمسة إلى إحداثيات داخل لوحة رسم مهما كان حجمها المعروض
  function canvasPoint(cv, e) {
    var r = cv.getBoundingClientRect(), p = point(e);
    return { x: (p.x - r.left) * cv.width / r.width, y: (p.y - r.top) * cv.height / r.height };
  }
  // صورة حقيقية جاهزة للرسم على لوحة، أو null إن لم توجد
  var imgCache = {};
  function photo(id) {
    if (!api.photos[id]) return null;
    if (!imgCache[id]) { imgCache[id] = new Image(); imgCache[id].src = 'img/' + id + '.jpg'; }
    return imgCache[id].complete && imgCache[id].naturalWidth ? imgCache[id] : null;
  }

  // ---------- النطق العربي ----------
  var arVoice = null;
  function findVoice() {
    if (!window.speechSynthesis || !speechSynthesis.getVoices) return;
    var v = speechSynthesis.getVoices();
    for (var i = 0; i < v.length; i++) if (v[i].lang && v[i].lang.indexOf('ar') === 0) { arVoice = v[i]; return; }
  }
  function say(text) {
    if (!data.sound || !window.speechSynthesis || !window.SpeechSynthesisUtterance) return;
    try {
      speechSynthesis.cancel();
      if (!arVoice) findVoice();
      var u = new SpeechSynthesisUtterance(text);
      u.lang = 'ar-SA'; if (arVoice) u.voice = arVoice;
      u.rate = 0.9;
      speechSynthesis.speak(u);
    } catch (e) {}
  }
  function hush() { try { if (window.speechSynthesis) speechSynthesis.cancel(); } catch (e) {} }

  // ---------- النجوم والملصقات ----------
  function refreshStars(bump) {
    var b = $('sbStars'); b.innerHTML = data.stars;
    if (bump) { b.className = ''; void b.offsetWidth; b.className = 'bump'; }
  }
  function addStars(n) { data.stars += n; save(); refreshStars(true); }
  // يمنح ملصقاً مرة واحدة فقط مع نجمة؛ يرجع true إذا كان جديداً
  function award(key, emoji, text) {
    if (data.awards[key]) return false;
    data.awards[key] = Date.now();
    addStars(1);
    toast(emoji || '⭐', (text || 'أحسنت!') + '<br>حصلت على نجمة ⭐', 2600);
    sfx('win');
    return true;
  }

  // ---------- الرسائل ----------
  var toastTimer = null;
  function toast(emoji, text, ms) {
    $('toastEmoji').innerHTML = emoji; $('toastText').innerHTML = text;
    var t = $('toast'); t.className = 'hidden'; void t.offsetWidth; t.className = '';
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.className = 'hidden'; }, ms || 1800);
    say(text.replace(/<[^>]+>/g, ' ').replace(/[\u2190-\u2BFF\uFE0F\uD800-\uDFFF]/g, ''));
  }
  // يعرض سؤالاً بأزرار: buttons = [{label, cls, fn}]
  function ask(html, buttons, speakText) {
    var box = $('modalBtns'); box.innerHTML = '';
    $('modalText').innerHTML = html;
    each(buttons, function (b) {
      var n = el('<button class="btn ' + (b.cls || '') + '">' + b.label + '</button>');
      tap(n, function () { $('modal').className = 'hidden'; sfx('click'); if (b.fn) b.fn(); });
      box.appendChild(n);
    });
    $('modal').className = '';
    if (speakText !== false) say(speakText || html.replace(/<[^>]+>/g, ' '));
  }

  // صورة حقيقية من ويكيميديا إن وُجدت (تُعرَّف في js/photos.js)، وإلا الرمز التعبيري
  function pic(id, fallback, cls) {
    return id && api.photos[id] ? '<img class="pic' + (cls ? ' ' + cls : '') + '" src="img/' + id + '.jpg" alt="">' : fallback;
  }

  // صندوق شرح مع زر «اقرأ لي»
  function info(html) {
    var n = el('<div class="info"><div class="speak">🔈</div><div class="txt">' + html + '</div></div>');
    tap(n.firstChild, function () { say(n.lastChild.innerHTML.replace(/<[^>]+>/g, ' ')); });
    n.set = function (h) { n.lastChild.innerHTML = h; };
    return n;
  }

  // ---------- الساعة ----------
  var DAYS = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت'];
  var MONTHS = ['كانون الثاني', 'شباط', 'آذار', 'نيسان', 'أيار', 'حزيران', 'تموز', 'آب', 'أيلول', 'تشرين الأول', 'تشرين الثاني', 'كانون الأول'];
  function pad(n) { return n < 10 ? '0' + n : '' + n; }
  function clock() {
    var d = new Date(), h = d.getHours() % 12; if (h === 0) h = 12;
    var t = h + ':' + pad(d.getMinutes());
    $('sbTime').innerHTML = t; $('lockTime').innerHTML = t;
    $('lockDate').innerHTML = DAYS[d.getDay()] + ' ' + d.getDate() + ' ' + MONTHS[d.getMonth()];
    var hr = d.getHours();
    var g = hr < 12 ? 'صباح الخير' : 'مساء الخير';
    var nm = data.name ? ' يا ' + data.name : '';
    $('greet').innerHTML = g + nm + ' ☀️ ماذا نتعلّم اليوم؟';
    $('lockHello').innerHTML = 'أهلاً' + nm + '! 👋';
    $('sbName').innerHTML = data.name ? '⭐ ' + data.name : 'نجوم';
  }

  // ---------- التطبيقات والنوافذ ----------
  function register(app) { apps.push(app); appById[app.id] = app; }

  function drawHome() {
    var grid = $('grid'), dock = $('dock');
    grid.innerHTML = ''; dock.innerHTML = '';
    each(apps, function (a) {
      var n = el('<div class="icon"><div class="icon-img" style="background:' + a.color + '">' + a.icon +
        (a.awards && countLeft(a) ? '<span class="icon-badge">' + countLeft(a) + '</span>' : '') +
        '</div><div class="icon-label">' + a.name + '</div></div>');
      tap(n, function () { open(a.id, n); });
      (a.dock ? dock : grid).appendChild(n);
    });
  }
  function countLeft(a) { var c = 0; each(a.awards, function (w) { if (!data.awards[w.key]) c++; }); return c; }

  function open(id, fromIcon) {
    var a = appById[id]; if (!a) return;
    if (current) closeWin(true);
    sfx('open'); hush();
    if (!a.win) {
      a.win = el('<div class="win closed"><div class="win-head" style="background:' + a.color + '">' +
        '<button class="btn btn-head" data-home>🏠</button><div class="win-title">' + a.icon + ' ' + a.name + '</div><div class="win-extra"></div></div>' +
        '<div class="win-body' + (a.scroll ? ' scroll' : '') + '"></div></div>');
      $('windows').appendChild(a.win);
      tap(a.win.querySelector('[data-home]'), function () { home(); });
      a.body = a.win.lastChild; a.extra = a.win.querySelector('.win-extra');
      a.ctl = a.build(a.body, a) || {};
    }
    if (fromIcon) {
      var r = fromIcon.getBoundingClientRect();
      var o = (r.left + r.width / 2) + 'px ' + (r.top + r.height / 2 - 40) + 'px';
      a.win.style.webkitTransformOrigin = o; a.win.style.transformOrigin = o;
    }
    a.win.style.display = '';
    void a.win.offsetWidth;
    a.win.className = 'win';
    current = a;
    data.opened[id] = (data.opened[id] || 0) + 1; save();
    setTimeout(function () { if (current === a && a.ctl.enter) a.ctl.enter(); }, 300);
  }
  function closeWin(instant) {
    var a = current; if (!a) return;
    current = null; hush();
    if (a.ctl.leave) a.ctl.leave();
    a.win.className = 'win closed';
    if (instant) a.win.style.display = 'none';
    else setTimeout(function () { if (current !== a) a.win.style.display = 'none'; }, 320);
  }
  function home() { if (!current) return; sfx('close'); closeWin(false); drawHome(); clock(); }

  function setWallpaper(w) {
    data.wallpaper = w; save();
    $('desk').className = w; $('lock').className = w;
  }

  // ---------- الإقلاع والقفل ----------
  function lock() {
    if (current) closeWin(true);
    $('lock').className = data.wallpaper;
    $('unlockKnob').style.right = '5px';
    clock();
  }
  function setupUnlock() {
    var knob = $('unlockKnob'), slider = $('unlockSlider'), startX = 0, dragging = false, max = 0;
    function down(e) { dragging = true; startX = point(e).x; max = slider.offsetWidth - knob.offsetWidth - 10; unlockAudio(); e.preventDefault(); }
    function move(e) {
      if (!dragging) return; e.preventDefault();
      var dx = startX - point(e).x; if (dx < 0) dx = 0; if (dx > max) dx = max;
      knob.style.right = (5 + dx) + 'px';
    }
    function up(e) {
      if (!dragging) return; dragging = false;
      var dx = startX - point(e).x;
      if (dx > max * 0.7) { sfx('open'); $('lock').className = 'hidden'; drawHome(); say($('greet').innerHTML.replace(/<[^>]+>/g, '')); }
      else knob.style.right = '5px';
    }
    knob.addEventListener('touchstart', down, false); knob.addEventListener('mousedown', down, false);
    document.addEventListener('touchmove', move, false); document.addEventListener('mousemove', move, false);
    document.addEventListener('touchend', up, false); document.addEventListener('mouseup', up, false);
  }

  // يمنع تمرير الصفحة ومطّها إلا داخل العناصر القابلة للتمرير
  function blockBounce() {
    document.addEventListener('touchmove', function (e) {
      var n = e.target;
      while (n && n !== document.body) {
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
    // iOS 9 لا يفتح الصوت إلا بعد رفع الإصبع
    document.addEventListener('touchend', unlockAudio, false);
    if (window.speechSynthesis) { findVoice(); speechSynthesis.onvoiceschanged = findVoice; }
    tap($('sbSound'), function () { data.sound = !data.sound; save(); $('sbSound').innerHTML = data.sound ? '🔊' : '🔇'; sfx('click'); });
    $('sbSound').innerHTML = data.sound ? '🔊' : '🔇';
    refreshStars(false);
    setupUnlock();
    setWallpaper(data.wallpaper);
    $('lock').className = 'hidden';
    clock(); setInterval(clock, 15000);

    // تحديث النسخة المخزّنة بلا إنترنت عند توفر نسخة أحدث
    try {
      var ac = window.applicationCache;
      if (ac) ac.addEventListener('updateready', function () { try { ac.swapCache(); } catch (e) {} location.reload(); }, false);
    } catch (e) {}

    var p = 0, fill = $('bootFill');
    var iv = setInterval(function () {
      p += 12; fill.style.width = Math.min(p, 100) + '%';
      if (p >= 110) { clearInterval(iv); $('boot').className = 'hidden'; lock(); }
    }, 120);
  }

  var api = {
    start: start, pic: pic, photos: {}, note: note, canvasPoint: canvasPoint, photo: photo, register: register, open: open, home: home, lock: lock,
    tap: tap, point: point, el: el, each: each, shuffle: shuffle, $: $,
    sfx: sfx, say: say, hush: hush, toast: toast, ask: ask, info: info,
    award: award, addStars: addStars, refreshStars: refreshStars,
    data: data, save: save, apps: apps, setWallpaper: setWallpaper,
    isOpen: function (id) { return current && current.id === id; }
  };
  return api;
})();
