/* الميزان: ضع شيئين في الكفّتين، وخمّن أيّهما أثقل. */
(function () {
  var ITEMS = [
    { p: 'leaf', e: '🍃', n: 'ورقة الشجر', w: 1 }, { p: 'balloon', e: '🎈', n: 'البالون', w: 2 },
    { p: 'pencil', e: '✏️', n: 'القلم', w: 3 }, { p: 'key', e: '🔑', n: 'المفتاح', w: 5 },
    { p: 'banana', e: '🍌', n: 'الموزة', w: 12 }, { p: 'apple', e: '🍎', n: 'التفاحة', w: 15 },
    { p: 'book', e: '📖', n: 'الكتاب', w: 40 }, { p: 'basketball', e: '🏀', n: 'الكرة', w: 60 },
    { p: 'anchor', e: '⚓', n: 'المرساة', w: 200 }
  ];
  var PX = 350, PY = 90, ARM = 220;
  var ICON = '<svg viewBox="0 0 100 100" width="100" height="100"><path d="M50,18 L50,86 M30,86 L70,86 M14,30 L86,30" stroke="#fff" stroke-width="7" stroke-linecap="round" fill="none"/>' +
    '<path d="M4,62 Q22,76 40,62 Z M60,62 Q78,76 96,62 Z" fill="#fff"/><path d="M14,30 L4,62 M14,30 L40,62 M86,30 L60,62 M86,30 L96,62" stroke="#fff" stroke-width="3"/></svg>';
  var scene, info, left = null, right = null, angle = 0, target = 0, raf = null, busy = false;

  function build(body) {
    var wrap = OS.el('<div></div>');
    info = OS.info('اختر شيئين لتضعهما في <b>الميزان</b>، ثم خمّن: أيّهما <b>أثقل</b>؟');
    scene = OS.el('<div class="panel" style="padding:0"></div>');
    var tray = OS.el('<div class="tray"></div>');
    OS.each(ITEMS, function (it, i) {
      var n = OS.el('<div class="item"><span class="em">' + OS.pic(it.p, it.e) + '</span>' + it.n + '</div>');
      OS.tap(n, function () { put(i); });
      tray.appendChild(n);
    });
    var row = OS.el('<div class="row"><button class="btn btn-white">🔄 أفرغ الكفّتين</button></div>');
    OS.tap(row.firstChild, empty);
    wrap.appendChild(info); wrap.appendChild(scene); wrap.appendChild(row); wrap.appendChild(tray);
    body.appendChild(wrap);
    render();
    return { enter: function () { OS.say(info.lastChild.innerHTML.replace(/<[^>]+>/g, ' ')); }, leave: function () { cancelAnimationFrame(raf); raf = null; angle = target; render(); } };
  }

  function put(i) {
    if (busy) return;
    if (left !== null && right !== null) empty(true);
    if (left === i || right === i) { OS.toast('🙂', 'اختر شيئاً مختلفاً للكفّة الأخرى'); return; }
    OS.sfx('pop');
    if (left === null) { left = i; render(); OS.say(ITEMS[i].n + '، والآن اختر شيئاً آخر'); return; }
    right = i; render();
    busy = true;
    setTimeout(function () {
      OS.ask('أيّ كفّة ستنزل إلى الأسفل؟', [
        { label: OS.pic(ITEMS[right].p, ITEMS[right].e) + ' ' + ITEMS[right].n, cls: 'btn-white', fn: function () { judge(right); } },
        { label: OS.pic(ITEMS[left].p, ITEMS[left].e) + ' ' + ITEMS[left].n, cls: 'btn-white', fn: function () { judge(left); } }
      ]);
    }, 300);
  }

  function judge(guess) {
    var L = ITEMS[left], R = ITEMS[right], heavy = R.w > L.w ? right : left;
    var light = heavy === right ? left : right;
    animateTo(heavy === right ? 0.32 : -0.32);
    setTimeout(function () {
      busy = false;
      var msg = ITEMS[heavy].n + ' أثقل من ' + ITEMS[light].n + '، لذلك نزلت كفّته.';
      if (guess === heavy) {
        OS.sfx('ding');
        var mem = OS.data.balance || (OS.data.balance = {}), key = Math.min(left, right) + '-' + Math.max(left, right);
        if (!mem[key]) { mem[key] = 1; OS.addStars(1); }
        var n = 0; for (var k in mem) n++;
        if (n >= 5 && OS.award('bal-5', '⭐', 'صرت خبيراً في الوزن!')) return;
        OS.toast('🎉', 'صحيح! ' + msg, 3000);
      } else { OS.sfx('buzz'); OS.toast('🤔', 'انظر! ' + msg, 3200); }
    }, 1100);
  }

  function empty(quiet) {
    left = right = null; animateTo(0);
    if (quiet !== true) OS.sfx('splash');
  }

  function animateTo(a) {
    target = a;
    if (raf) return;
    (function tick() {
      angle += (target - angle) * 0.12;
      if (Math.abs(target - angle) < 0.002) { angle = target; raf = null; render(); return; }
      render(); raf = requestAnimationFrame(tick);
    })();
  }

  function pan(x, y, idx) {
    var s = '<line x1="' + x + '" y1="' + y + '" x2="' + (x - 70) + '" y2="' + (y + 120) + '" stroke="#78909c" stroke-width="3"/>' +
      '<line x1="' + x + '" y1="' + y + '" x2="' + (x + 70) + '" y2="' + (y + 120) + '" stroke="#78909c" stroke-width="3"/>' +
      '<path d="M' + (x - 85) + ',' + (y + 120) + ' Q' + x + ',' + (y + 175) + ' ' + (x + 85) + ',' + (y + 120) + ' Z" fill="#ffb300" stroke="#e65100" stroke-width="3"/>';
    if (idx !== null) {
      var it = ITEMS[idx];
      if (OS.photos[it.p]) s += '<image x="' + (x - 40) + '" y="' + (y + 40) + '" width="80" height="80" xlink:href="img/' + it.p + '.jpg"/>';
      else s += '<text x="' + x + '" y="' + (y + 112) + '" font-size="64" text-anchor="middle">' + it.e + '</text>';
    }
    return s;
  }

  function render() {
    var c = Math.cos(angle), sn = Math.sin(angle);
    var lx = PX - ARM * c, ly = PY - ARM * sn, rx = PX + ARM * c, ry = PY + ARM * sn;
    scene.innerHTML = '<svg viewBox="0 0 700 380" width="100%" height="330" xmlns:xlink="http://www.w3.org/1999/xlink" style="display:block">' +
      '<rect width="700" height="380" fill="#fff8e1"/>' +
      '<path d="M' + PX + ',' + PY + ' L' + PX + ',350 M' + (PX - 80) + ',356 L' + (PX + 80) + ',356" stroke="#5d4037" stroke-width="14" stroke-linecap="round"/>' +
      '<line x1="' + lx + '" y1="' + ly + '" x2="' + rx + '" y2="' + ry + '" stroke="#6d4c41" stroke-width="12" stroke-linecap="round"/>' +
      '<circle cx="' + PX + '" cy="' + PY + '" r="12" fill="#ffca28"/>' +
      pan(lx, ly, left) + pan(rx, ry, right) + '</svg>';
  }

  OS.register({
    id: 'balance', name: 'الميزان', icon: ICON, color: '#ad1457', build: build, scroll: true,
    awards: [{ key: 'bal-5', e: '⭐', l: 'خبير الوزن' }]
  });
})();
