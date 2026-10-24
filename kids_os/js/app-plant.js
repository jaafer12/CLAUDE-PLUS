/* نمو النبتة: كل سقاية والشمس مشرقة تكبر النبتة خطوة حتى تُزهر. بلا شمس لا تكبر. */
(function () {
  var STAGES = ['بذرة', 'برعم صغير', 'نبتة صغيرة', 'نبتة كبيرة', 'زهرة'];
  var scene, info, dayEl, sunBtn;
  var stage = 0, sun = true, busy = false;

  function build(body) {
    var wrap = OS.el('<div></div>');
    info = OS.info('');
    var panel = OS.el('<div class="panel" style="padding:0;overflow:hidden;border-radius:22px"></div>');
    scene = OS.el('<div></div>'); panel.appendChild(scene);
    dayEl = OS.el('<div class="title2"></div>');
    var row = OS.el('<div class="row"></div>');
    row.appendChild(OS.iconBtn('water', '#3b82f6', 'اسقِ', waterIt));
    sunBtn = OS.iconBtn('sun', '#f59e0b', 'الشمس', toggleSun);
    row.appendChild(sunBtn);
    row.appendChild(OS.iconBtn('reset', '#94a3b8', 'بذرة جديدة', restart));
    wrap.appendChild(info); wrap.appendChild(dayEl); wrap.appendChild(panel); wrap.appendChild(row);
    body.appendChild(wrap);
    restart(true);
    return { enter: function () {  } };
  }

  function restart() {
    stage = 0; sun = true; busy = false;
    info.set('النبتة تحتاج <b>الماء</b> و<b>ضوء الشمس</b> لتكبر. كل سقاية والشمس مشرقة تكبر النبتة خطوة. إذا غطّت الغيوم الشمس لا تكبر.');
    render(false);
  }

  function waterIt() {
    if (busy) return;
    if (stage >= 4) { restart(); return; }
    busy = true;
    render(true);
    setTimeout(function () {
      busy = false;
      if (!sun) { render(false); OS.hint('النبتة تحتاج الشمس لتكبر', 2200); return; }
      stage++;
      render(false);
      if (stage === 4) OS.award('p-flower', '', 'زرعت زهرة بنفسك!');
    }, 900);
  }
  function toggleSun() { sun = !sun; render(false); }

  function render(rain) {
    dayEl.innerHTML = STAGES[stage];
    sunBtn.on(sun);
    var sky = sun ? '#81d4fa' : '#b0bec5', w = 700, h = 300, cx = 350, ground = 240;
    var leaf = '#43a047';
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
    if (rain) for (var d = 0; d < 7; d++) s += '<path d="M' + (cx - 60 + d * 20) + ',' + (top - 60 + (d % 2) * 20) + ' q-7,12 0,16 q7,-4 0,-16z" fill="#38bdf8"/>';
    s += '</svg>';
    scene.innerHTML = s;
  }

  OS.register({
    id: 'plant', name: 'نمو النبتة', icon: 'sprout', color: '#22c55e', shade: '#15803d', build: build, scroll: true,
    awards: [{ key: 'p-flower', e: '🌸', l: 'المزارع الصغير' }]
  });
})();
