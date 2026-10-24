/* يطفو أم يغرق: يتوقّع الطفل ثم يرى الجسم في الماء. */
(function () {
  var ITEMS = [
    { e: '🍎', n: 'التفاحة', f: true, why: 'في التفاحة هواء كثير، فهي أخف من الماء وتطفو.' },
    { e: '🔑', n: 'المفتاح', f: false, why: 'المفتاح من المعدن الثقيل، فهو أثقل من الماء ويغرق.' },
    { e: '🍃', n: 'ورقة الشجر', f: true, why: 'ورقة الشجر خفيفة جداً فتطفو فوق الماء.' },
    { e: '⚓', n: 'المرساة', f: false, why: 'المرساة حديد ثقيل، لذلك تغرق وتثبّت السفينة.' },
    { e: '🏀', n: 'الكرة', f: true, why: 'الكرة مملوءة بالهواء، والهواء يجعلها تطفو.' },
    { e: '💍', n: 'الخاتم', f: false, why: 'الخاتم صغير لكنه من معدن ثقيل فيغرق.' },
    { e: '✏️', n: 'قلم الخشب', f: true, why: 'الخشب أخف من الماء، لذلك يطفو.' },
    { e: '🔩', n: 'البرغي', f: false, why: 'البرغي من الحديد، والحديد أثقل من الماء.' },
    { e: '🍋', n: 'الليمونة', f: true, why: 'قشرة الليمون فيها فقاعات هواء صغيرة فتطفو.' },
    { e: '🎾', n: 'كرة التنس', f: true, why: 'كرة التنس فارغة من الداخل ومملوءة بالهواء.' }
  ];
  var tank, info, tray, slots = 0;

  function build(body) {
    var wrap = OS.el('<div></div>');
    info = OS.info('بعض الأشياء <b>تطفو</b> فوق الماء، وبعضها <b>يغرق</b> إلى القاع. اختر شيئاً، وخمّن ماذا سيحدث له!');
    tank = OS.el('<div class="tank"><div class="tank-water"></div></div>');
    tray = OS.el('<div class="tray"></div>');
    var reset = OS.el('<div class="row"><button class="btn btn-white">🔄 أفرغ الحوض</button></div>');
    OS.tap(reset.firstChild, empty);
    wrap.appendChild(info); wrap.appendChild(tank); wrap.appendChild(reset); wrap.appendChild(tray);
    body.appendChild(wrap);
    fillTray();
    return { enter: function () { OS.say(info.lastChild.innerHTML.replace(/<[^>]+>/g, ' ')); } };
  }

  function fillTray() {
    var done = OS.data.floatDone || {};
    tray.innerHTML = '';
    OS.each(ITEMS, function (it, i) {
      var n = OS.el('<div class="item' + (done[i] ? ' done' : '') + '"><span class="em">' + it.e + '</span>' + it.n + '</div>');
      OS.tap(n, function () {
        OS.sfx('click');
        OS.ask(it.e + '<br>ماذا سيحدث لـ' + it.n + ' في الماء؟', [
          { label: '⬆️ تطفو', cls: 'btn-teal', fn: function () { drop(i, n, true); } },
          { label: '⬇️ تغرق', cls: 'btn-blue', fn: function () { drop(i, n, false); } }
        ]);
      });
      tray.appendChild(n);
    });
  }

  function empty() { OS.sfx('splash'); var o = tank.querySelectorAll('.tank-obj'); for (var i = 0; i < o.length; i++) tank.removeChild(o[i]); slots = 0; }

  function drop(i, node, said) {
    var it = ITEMS[i], H = tank.offsetHeight, surface = H * 0.28;
    if (slots >= 8) empty();
    var x = 10 + (slots % 8) * 11.5 + 2;
    slots++;
    var o = OS.el('<div class="tank-obj fast" style="left:' + x + '%;top:-70px">' + it.e + '</div>');
    tank.appendChild(o);
    void o.offsetWidth;
    o.style.top = (surface + 10) + 'px';
    setTimeout(function () {
      OS.sfx('splash');
      o.className = 'tank-obj';
      o.style.top = it.f ? (surface - 40) + 'px' : (H - 70) + 'px';
    }, 520);
    setTimeout(function () {
      var done = OS.data.floatDone || (OS.data.floatDone = {});
      if (said === it.f) {
        OS.sfx('ding');
        if (!done[i]) { done[i] = 1; OS.addStars(1); node.className = 'item done'; }
        OS.toast(it.f ? '⬆️' : '⬇️', 'صحيح! ' + it.why, 3200);
      } else {
        OS.sfx('buzz'); OS.toast('🤔', 'انظر! ' + it.why, 3600);
      }
      var all = true; for (var k = 0; k < ITEMS.length; k++) if (!done[k]) all = false;
      if (all) setTimeout(function () { OS.award('f-all', '🚢', 'أصبحت خبيراً في الطفو والغرق!'); }, 3700);
    }, 2200);
  }

  OS.register({
    id: 'float', name: 'يطفو أم يغرق', icon: '🚢', color: '#00acc1', build: build, scroll: true,
    awards: [{ key: 'f-all', e: '🚢', l: 'يطفو أم يغرق' }]
  });
})();
