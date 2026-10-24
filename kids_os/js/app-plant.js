/* نمو النبتة: الماء + ضوء الشمس كل يوم = نبتة تكبر حتى تُزهر. */
(function () {
  var STAGES = ['بذرة', 'برعم صغير', 'نبتة صغيرة', 'نبتة كبيرة', 'زهرة'];
  var scene, info, dayEl, sunBtn;
  var stage = 0, day = 1, water = 0, sun = true, thirsty = 0;

  function build(body) {
    var wrap = OS.el('<div></div>');
    info = OS.info('');
    var panel = OS.el('<div class="panel" style="padding:0;overflow:hidden;border-radius:22px"></div>');
    scene = OS.el('<div></div>'); panel.appendChild(scene);
    dayEl = OS.el('<div class="title2"></div>');
    var row = OS.el('<div class="row"></div>');
    var wBtn = OS.el('<button class="btn btn-blue">💧 اسقِ النبتة</button>');
    sunBtn = OS.el('<button class="btn btn-orange">☀️ الشمس</button>');
    var dBtn = OS.el('<button class="btn btn-green">🌙 نامي… يوم جديد</button>');
    var rBtn = OS.el('<button class="btn btn-white">🔄 بذرة جديدة</button>');
    OS.tap(wBtn, waterIt); OS.tap(sunBtn, toggleSun); OS.tap(dBtn, nextDay); OS.tap(rBtn, restart);
    row.appendChild(wBtn); row.appendChild(sunBtn); row.appendChild(dBtn); row.appendChild(rBtn);
    wrap.appendChild(info); wrap.appendChild(dayEl); wrap.appendChild(panel); wrap.appendChild(row);
    body.appendChild(wrap);
    restart(true);
    return { enter: function () { OS.say(info.lastChild.innerHTML.replace(/<[^>]+>/g, ' ')); } };
  }

  function restart(quiet) {
    stage = 0; day = 1; water = 0; sun = true; thirsty = 0;
    info.set('اسقِ البذرة 💧 واتركها في الشمس ☀️ ثم اضغط «يوم جديد».');
    render(false);
    if (quiet !== true) OS.sfx('pop');
  }

  function waterIt() {
    water++;
    OS.sfx('splash');
    render(true);
    if (water === 1) OS.say('شربت النبتة الماء، شكراً!');
    else if (water === 2) OS.say('هذا يكفي لليوم');
    else OS.toast('🌊', 'كفى! الماء الكثير جداً يضرّ الجذور');
  }
  function toggleSun() { sun = !sun; OS.sfx('click'); render(false); OS.say(sun ? 'أشرقت الشمس' : 'غطّت الغيوم الشمس'); }

  function nextDay() {
    OS.sfx('click');
    var msg;
    if (stage >= 4) { OS.toast('🌸', 'النبتة أزهرت! ازرع بذرة جديدة'); return; }
    if (water === 0) { thirsty++; msg = ['😟', 'النبتة عطشى! لم تشرب الماء فلم تكبر']; }
    else if (water > 2) { msg = ['🌊', 'الماء كان كثيراً جداً، النبتة لم تكبر اليوم']; }
    else if (!sun) { msg = ['☁️', 'لم ترَ النبتة ضوء الشمس فلم تكبر. النبتة تحتاج الضوء لتصنع غذاءها']; }
    else { stage++; thirsty = 0; msg = null; }
    day++; water = 0;
    render(false);
    if (msg) { OS.sfx('buzz'); OS.toast(msg[0], msg[1], 3200); return; }
    OS.sfx('ding');
    if (stage === 4) {
      info.set('🌸 رائع! بالماء والشمس صارت البذرة <b>زهرة</b>.');
      OS.award('p-flower', '🌸', 'زرعت زهرة بنفسك!');
    } else OS.toast('🌱', 'كبرت النبتة! صارت ' + STAGES[stage]);
  }

  function render(rain) {
    dayEl.innerHTML = 'اليوم ' + day + ' — ' + STAGES[stage] + (water ? ' ' + new Array(Math.min(water, 3) + 1).join('💧') : '');
    sunBtn.innerHTML = sun ? '☀️ الشمس مشرقة' : '☁️ غائم';
    var sky = sun ? '#81d4fa' : '#b0bec5', w = 700, h = 300, cx = 350, ground = 240;
    var leaf = thirsty ? '#c0ca33' : '#43a047';
    var s = '<svg viewBox="0 0 ' + w + ' ' + h + '" width="100%" height="300" style="display:block">';
    s += '<rect width="' + w + '" height="' + h + '" fill="' + sky + '"/>';
    if (sun) s += '<circle cx="90" cy="70" r="44" fill="#ffeb3b"/><circle cx="90" cy="70" r="60" fill="#ffeb3b" opacity=".3"/>';
    else s += '<g fill="#eceff1"><circle cx="90" cy="70" r="34"/><circle cx="130" cy="60" r="40"/><circle cx="170" cy="76" r="30"/></g>';
    s += '<rect y="' + ground + '" width="' + w + '" height="' + (h - ground) + '" fill="#8d6e63"/>';
    // الساق والأوراق حسب المرحلة
    var stem = [0, 30, 70, 120, 150][stage], top = ground - stem;
    if (stage === 0) s += '<ellipse cx="' + cx + '" cy="' + (ground + 14) + '" rx="12" ry="8" fill="#5d4037"/>';
    if (stage >= 1) s += '<path d="M' + cx + ',' + ground + ' L' + cx + ',' + top + '" stroke="' + leaf + '" stroke-width="8" stroke-linecap="round"/>';
    var pairs = stage === 1 ? 1 : stage === 2 ? 2 : stage >= 3 ? 3 : 0;
    for (var i = 0; i < pairs; i++) {
      var y = ground - 18 - i * (stem - 20) / Math.max(pairs, 1), l = 22 + i * 4;
      s += '<ellipse cx="' + (cx - l) + '" cy="' + y + '" rx="' + l + '" ry="10" fill="' + leaf + '" transform="rotate(-25 ' + (cx - l) + ' ' + y + ')"/>';
      s += '<ellipse cx="' + (cx + l) + '" cy="' + y + '" rx="' + l + '" ry="10" fill="' + leaf + '" transform="rotate(25 ' + (cx + l) + ' ' + y + ')"/>';
    }
    if (stage === 3) s += '<circle cx="' + cx + '" cy="' + top + '" r="12" fill="#66bb6a"/>';
    if (stage === 4) {
      for (var k = 0; k < 6; k++) {
        var a = k * Math.PI / 3;
        s += '<circle cx="' + (cx + 24 * Math.cos(a)) + '" cy="' + (top + 24 * Math.sin(a)) + '" r="18" fill="#ec407a"/>';
      }
      s += '<circle cx="' + cx + '" cy="' + top + '" r="14" fill="#ffca28"/>';
    }
    // الإصيص
    s += '<path d="M' + (cx - 70) + ',' + (ground - 6) + ' L' + (cx + 70) + ',' + (ground - 6) + ' L' + (cx + 52) + ',' + (h - 4) + ' L' + (cx - 52) + ',' + (h - 4) + ' Z" fill="#d84315"/>';
    s += '<rect x="' + (cx - 78) + '" y="' + (ground - 16) + '" width="156" height="18" rx="6" fill="#bf360c"/>';
    if (rain) for (var d = 0; d < 7; d++) s += '<text x="' + (cx - 60 + d * 20) + '" y="' + (top - 40 + (d % 2) * 20) + '" font-size="26">💧</text>';
    s += '</svg>';
    scene.innerHTML = s;
  }

  OS.register({
    id: 'plant', name: 'نمو النبتة', icon: '🌱', color: '#2e7d32', build: build, scroll: true,
    awards: [{ key: 'p-flower', e: '🌸', l: 'المزارع الصغير' }]
  });
})();
