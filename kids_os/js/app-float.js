/* يطفو أم يغرق: يضغط الطفل على شيء فيسقط في الماء ويرى هل يطفو أم يغرق. */
(function () {
  var ITEMS = [
    { p: 'apple', e: '🍎', n: 'التفاحة', f: true, why: 'في التفاحة هواء كثير، فهي أخف من الماء وتطفو.' },
    { p: 'key', e: '🔑', n: 'المفتاح', f: false, why: 'المفتاح من المعدن الثقيل، فهو أثقل من الماء ويغرق.' },
    { p: 'leaf', e: '🍃', n: 'ورقة الشجر', f: true, why: 'ورقة الشجر خفيفة جداً فتطفو فوق الماء.' },
    { p: 'anchor', e: '⚓', n: 'المرساة', f: false, why: 'المرساة حديد ثقيل، لذلك تغرق وتثبّت السفينة.' },
    { p: 'basketball', e: '🏀', n: 'الكرة', f: true, why: 'الكرة مملوءة بالهواء، والهواء يجعلها تطفو.' },
    { p: 'ring', e: '💍', n: 'الخاتم', f: false, why: 'الخاتم صغير لكنه من معدن ثقيل فيغرق.' },
    { p: 'pencil', e: '✏️', n: 'قلم الخشب', f: true, why: 'الخشب أخف من الماء، لذلك يطفو.' },
    { p: 'bolt', e: '🔩', n: 'البرغي', f: false, why: 'البرغي من الحديد، والحديد أثقل من الماء.' },
    { p: 'lemon', e: '🍋', n: 'الليمونة', f: true, why: 'قشرة الليمون فيها فقاعات هواء صغيرة فتطفو.' },
    { p: 'tennisball', e: '🎾', n: 'كرة التنس', f: true, why: 'كرة التنس فارغة من الداخل ومملوءة بالهواء.' }
  ];
  var tank, info, tray, slots = 0;

  function build(body) {
    var wrap = OS.el('<div></div>');
    info = OS.info('اختر شيئاً وخمّن: هل <b>يطفو</b> أم <b>يغرق</b>؟');
    tank = OS.el('<div class="tank"><div class="tank-water"></div></div>');
    tray = OS.el('<div class="tray"></div>');
    var reset = OS.el('<div class="row"></div>');
    reset.appendChild(OS.iconBtn('reset', '#94a3b8', 'أفرغ الحوض', empty));
    wrap.appendChild(info); wrap.appendChild(tank); wrap.appendChild(reset); wrap.appendChild(tray);
    body.appendChild(wrap);
    fillTray();
    return { enter: function () {  } };
  }

  function fillTray() {
    var done = OS.data.floatDone || {};
    tray.innerHTML = '';
    OS.each(ITEMS, function (it, i) {
      var n = OS.el('<div class="item' + (done[i] ? ' done' : '') + '"><span class="em">' + OS.pic(it.p, it.e) + '</span>' + it.n + '</div>');
      OS.tap(n, function () { drop(i, n); });
      tray.appendChild(n);
    });
  }

  function empty() { var o = tank.querySelectorAll('.tank-obj'); for (var i = 0; i < o.length; i++) tank.removeChild(o[i]); slots = 0; }

  function drop(i, node) {
    var it = ITEMS[i], H = tank.offsetHeight, surface = H * 0.28;
    if (slots >= 8) empty();
    var x = 10 + (slots % 8) * 11.5 + 2;
    slots++;
    var o = OS.el('<div class="tank-obj fast" style="left:' + x + '%;top:-70px">' + OS.pic(it.p, it.e, 'obj') + '</div>');
    tank.appendChild(o);
    void o.offsetWidth;
    o.style.top = (surface + 10) + 'px';
    setTimeout(function () {
      o.className = 'tank-obj';
      o.style.top = it.f ? (surface - 40) + 'px' : (H - 70) + 'px';
    }, 520);
    setTimeout(function () {
      var done = OS.data.floatDone || (OS.data.floatDone = {});
      if (!done[i]) { done[i] = 1; OS.addStars(1); node.className = 'item done'; }
      OS.ok(it.why, 2600);
      var all = true; for (var k = 0; k < ITEMS.length; k++) if (!done[k]) all = false;
      if (all) setTimeout(function () { OS.award('f-all', '🚢', 'أصبحت خبيراً في الطفو والغرق!'); }, 3700);
    }, 1900);
  }

  OS.register({
    id: 'float', name: 'يطفو أم يغرق', icon: 'boat', color: '#06b6d4', shade: '#0e7490', build: build, scroll: true,
    awards: [{ key: 'f-all', e: '🚢', l: 'يطفو أم يغرق' }]
  });
})();
