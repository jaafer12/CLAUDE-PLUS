/* خلط الألوان: اسكب لونين في الوعاء واكتشف اللون الجديد. */
(function () {
  var POTS = [['red', 'أحمر', '#e53935'], ['yellow', 'أصفر', '#fdd835'], ['blue', 'أزرق', '#1e88e5'], ['white', 'أبيض', '#ffffff']];
  var MIX = {
    'red+yellow': ['برتقالي', '#fb8c00'], 'blue+red': ['بنفسجي', '#8e24aa'], 'blue+yellow': ['أخضر', '#43a047'],
    'red+white': ['وردي', '#f48fb1'], 'blue+white': ['سماوي', '#81d4fa'], 'white+yellow': ['أصفر فاتح', '#fff59d']
  };
  var COUNT = 6;
  var bowl, eq, found, info, picks = [];

  function name(id) { for (var i = 0; i < POTS.length; i++) if (POTS[i][0] === id) return POTS[i]; }

  function build(body) {
    var wrap = OS.el('<div></div>');
    info = OS.info('اضغط على <b>لونين</b> واكتشف اللون الجديد!');
    var pots = OS.el('<div class="row"></div>');
    OS.each(POTS, function (p) {
      var n = OS.el('<div class="pot" style="background:' + p[2] + (p[0] === 'white' || p[0] === 'yellow' ? ';color:#555;text-shadow:none' : '') + '">' + p[1] + '</div>');
      OS.tap(n, function () { pour(p, n); });
      pots.appendChild(n);
    });
    bowl = OS.el('<div class="bowl"></div>');
    eq = OS.el('<div class="eq"></div>');
    found = OS.el('<div class="found"></div>');
    var again = OS.el('<div class="row"><button class="btn btn-white">وعاء نظيف</button></div>');
    OS.tap(again.firstChild, clean);
    wrap.appendChild(info); wrap.appendChild(pots); wrap.appendChild(bowl); wrap.appendChild(eq); wrap.appendChild(again); wrap.appendChild(found);
    body.appendChild(wrap);
    showFound();
    return { enter: function () {  } };
  }

  function chip(c) { return '<span class="chip-c" style="background:' + c + '"></span>'; }

  function clean() { picks = []; bowl.style.backgroundColor = '#fafafa'; eq.innerHTML = ''; }

  function pour(p, pot) {
    if (picks.length >= 2) clean();
    picks.push(p[0]);
        var a = pot.getBoundingClientRect(), b = bowl.getBoundingClientRect();
    var d = OS.el('<div class="drop" style="background:' + p[2] + ';left:' + (a.left + a.width / 2 - 17) + 'px;top:' + (a.top + a.height / 2) + 'px"></div>');
    document.body.appendChild(d);
    void d.offsetWidth;
    d.style.left = (b.left + b.width / 2 - 17) + 'px'; d.style.top = (b.top + 30) + 'px';
    setTimeout(function () { document.body.removeChild(d); mixNow(); }, 650);
  }

  function mixNow() {
    if (picks.length === 1) {
      var one = name(picks[0]);
      bowl.style.backgroundColor = one[2];
      eq.innerHTML = chip(one[2]) + ' + ؟';
      return;
    }
    var a = name(picks[0]), b = name(picks[1]);
    if (picks[0] === picks[1]) {
      eq.innerHTML = chip(a[2]) + ' + ' + chip(a[2]) + ' = ' + chip(a[2]) + ' ' + a[1];
      OS.hint('ما زال ' + a[1] + '! اللون مع نفسه لا يتغيّر'); return;
    }
    var key = [picks[0], picks[1]].sort().join('+'), r = MIX[key];
    bowl.style.backgroundColor = r[1];
    eq.innerHTML = chip(a[2]) + ' + ' + chip(b[2]) + ' = ' + chip(r[1]) + ' ' + r[0];
    var mem = OS.data.colors || (OS.data.colors = {});
        if (!mem[key]) {
      mem[key] = 1; OS.addStars(1);
      OS.ok('اكتشفت لوناً جديداً!<br>' + a[1] + ' و' + b[1] + ' = ' + r[0]);
      var n = 0; for (var k in mem) n++;
      if (n >= COUNT) setTimeout(function () { OS.award('col-all', '🎨', 'اكتشفت كل الألوان! أنت فنان'); }, 2000);
    }
    showFound();
  }

  function showFound() {
    var mem = OS.data.colors || {}, s = '', n = 0;
    for (var k in MIX) if (mem[k]) { s += chip(MIX[k][1]); n++; }
    found.innerHTML = 'الألوان التي اكتشفتها (' + n + ' من ' + COUNT + '): ' + (s || '—');
  }

  OS.register({
    id: 'colors', name: 'خلط الألوان', icon: 'palette', color: '#ec4899', shade: '#be185d', build: build, scroll: true,
    awards: [{ key: 'col-all', e: '🎨', l: 'فنان الألوان' }]
  });
})();
