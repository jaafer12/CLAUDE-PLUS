/* المغناطيس: اسحب المغناطيس فوق الطاولة واكتشف ما ينجذب إليه. */
(function () {
  var ITEMS = [
    { p: 'paperclip', e: '📎', n: 'مشبك', m: true, x: 15, y: 30 }, { p: 'bolt', e: '🔩', n: 'برغي', m: true, x: 80, y: 75 },
    { p: 'scissors', e: '✂️', n: 'مقص', m: true, x: 35, y: 80 }, { p: 'wrench', e: '🔧', n: 'مفتاح ربط', m: true, x: 88, y: 30 },
    { p: 'pencil', e: '✏️', n: 'قلم خشب', m: false, x: 12, y: 70 }, { p: 'apple', e: '🍎', n: 'تفاحة', m: false, x: 62, y: 85 },
    { p: 'balloon', e: '🎈', n: 'بالون', m: false, x: 70, y: 22 }, { p: 'ruler', e: '📏', n: 'مسطرة', m: false, x: 30, y: 50 },
    { p: 'leaf', e: '🍃', n: 'ورقة', m: false, x: 85, y: 52 }
  ];
  var SLOTS = [[-38, 18], [38, 18], [0, 34], [-60, 44], [60, 44], [0, 64]];
  var MAG = '<svg viewBox="0 0 120 130" width="120" height="130"><path d="M25,125 L25,58 A35,35 0 0 1 95,58 L95,125" stroke="#e53935" stroke-width="32" fill="none"/>' +
    '<line x1="25" y1="100" x2="25" y2="128" stroke="#cfd8dc" stroke-width="32"/><line x1="95" y1="100" x2="95" y2="128" stroke="#cfd8dc" stroke-width="32"/></svg>';

  var area, mag, info, nodes = [], mx = 0, my = 0, drag = null, stuck = 0, W = 0, H = 0;

  function build(body, app) {
    info = OS.info('<b>المغناطيس</b> يجذب الأشياء المصنوعة من <b>الحديد</b>. اسحب المغناطيس الأحمر بإصبعك فوق الأشياء: أيّها يلتصق به؟');
    area = OS.el('<div class="table" style="top:100px"><div class="mag-hint">✋ اسحب المغناطيس</div></div>');
    body.appendChild(info); body.appendChild(area);
    var reset = OS.el('<button class="btn btn-head">🔄 من جديد</button>');
    OS.tap(reset, function () { OS.sfx('click'); place(); });
    app.extra.appendChild(reset);
    OS.each(ITEMS, function (it) {
      var n = OS.el('<div class="mag-obj">' + OS.pic(it.p, it.e, 'obj') + '<div class="nm">' + it.n + '</div></div>');
      area.appendChild(n); nodes.push(n);
    });
    mag = OS.el('<div class="magnet">' + MAG + '</div>');
    area.appendChild(mag);
    mag.addEventListener('touchstart', down, false); mag.addEventListener('mousedown', down, false);
    document.addEventListener('touchmove', move, false); document.addEventListener('mousemove', move, false);
    document.addEventListener('touchend', up, false); document.addEventListener('mouseup', up, false);
    window.addEventListener('resize', function () { if (OS.isOpen('magnet')) setTimeout(place, 300); }, false);
    return { enter: function () { place(); OS.say(info.lastChild.innerHTML.replace(/<[^>]+>/g, ' ')); } };
  }

  function place() {
    area.style.top = (info.offsetHeight + 20) + 'px';
    W = area.offsetWidth; H = area.offsetHeight; stuck = 0;
    OS.each(ITEMS, function (it, i) {
      it.st = -1; it.px = W * it.x / 100; it.py = H * it.y / 100; it.warn = 0;
      nodes[i].className = 'mag-obj';
      pos(nodes[i], it.px, it.py);
    });
    mx = W / 2; my = H * 0.42; moveMag();
  }
  function pos(n, x, y) { n.style.left = x + 'px'; n.style.top = y + 'px'; }
  function moveMag() {
    pos(mag, mx, my - 110);
    OS.each(ITEMS, function (it, i) { if (it.st >= 0) pos(nodes[i], mx + SLOTS[it.st][0], my + SLOTS[it.st][1]); });
  }

  function down(e) { e.preventDefault(); var p = OS.point(e); drag = { dx: mx - p.x, dy: my - p.y }; OS.sfx('click'); }
  function move(e) {
    if (!drag) return; e.preventDefault();
    var p = OS.point(e);
    mx = Math.max(40, Math.min(W - 40, p.x + drag.dx));
    my = Math.max(110, Math.min(H - 10, p.y + drag.dy));
    moveMag(); sense();
  }
  function up() { drag = null; }

  function sense() {
    var now = Date.now();
    OS.each(ITEMS, function (it, i) {
      if (it.st >= 0) return;
      var dx = it.px - mx, dy = it.py - my, d = Math.sqrt(dx * dx + dy * dy);
      if (it.m && d < 110) {
        it.st = stuck++; nodes[i].className = 'mag-obj stuck';
        OS.sfx('pop'); OS.say('انجذب ' + it.n + '!');
        moveMag();
        var all = true; OS.each(ITEMS, function (t) { if (t.m && t.st < 0) all = false; });
        if (all) setTimeout(function () { OS.award('m-all', '📎', 'وجدت كل أشياء الحديد! المغناطيس يجذب الحديد فقط'); }, 600);
      } else if (!it.m && d < 80 && now - it.warn > 2500) {
        it.warn = now;
        var n = nodes[i]; n.className = 'mag-obj'; void n.offsetWidth; n.className = 'mag-obj wiggle';
        OS.sfx('buzz'); OS.say(it.n + ' لا ينجذب، ليس من الحديد');
      }
    });
  }

  OS.register({
    id: 'magnet', name: 'المغناطيس', icon: MAG, color: '#7e57c2', build: build,
    awards: [{ key: 'm-all', e: '📎', l: 'صيّاد الحديد' }]
  });
})();
