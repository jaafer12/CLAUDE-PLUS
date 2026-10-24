/* حالات الماء: ثلج ← ماء ← بخار. جزيئات متحركة تتغير حركتها مع درجة الحرارة. */
(function () {
  var cv, ctx, info, slider, stateEl, heatBtn, coolBtn, raf = null;
  var temp = 20, dir = 0, parts = [], last = '';
  var L = 70, R = 370, T = 40, B = 340, PR = 9; // حدود الإناء داخل اللوحة

  var TEXT = {
    solid: '❄️ <b>ثلج</b>: بارد جداً، جزيئاته ثابتة في مكانها.',
    liquid: '💧 <b>ماء</b>: جزيئاته تتحرّك وتجري. سخّنه أو برّده!',
    gas: '☁️ <b>بخار</b>: حارّ جداً، جزيئاته تطير بسرعة.'
  };

  function state() { return temp < 0 ? 'solid' : temp < 100 ? 'liquid' : 'gas'; }

  function build(body) {
    var wrap = OS.el('<div></div>');
    info = OS.info(TEXT.liquid);
    var panel = OS.el('<div class="panel row" style="padding:6px"></div>');
    cv = document.createElement('canvas'); cv.width = 520; cv.height = 420; cv.style.width = '520px'; cv.style.height = '420px';
    ctx = cv.getContext('2d');
    var side = OS.el('<div style="width:300px;text-align:center"></div>');
    stateEl = OS.el('<div class="title2" style="font-size:34px;min-height:60px"></div>');
    heatBtn = OS.el('<button class="btn btn-red" style="width:240px">🔥 سخّن</button>');
    coolBtn = OS.el('<button class="btn btn-blue" style="width:240px">❄️ برّد</button>');
    slider = OS.el('<input type="range" dir="ltr" min="-30" max="130" step="1" value="20" style="width:240px;margin:16px 0;direction:ltr">');
    side.appendChild(stateEl); side.appendChild(heatBtn); side.appendChild(coolBtn); side.appendChild(slider);
    side.appendChild(OS.el('<div style="font-size:17px;color:#78909c">أو حرّك المؤشر لتغيير الحرارة</div>'));
    panel.appendChild(cv); panel.appendChild(side);
    wrap.appendChild(info); wrap.appendChild(panel);
    body.appendChild(wrap);

    OS.tap(heatBtn, function () { dir = dir === 1 ? 0 : 1; OS.sfx('click'); btns(); });
    OS.tap(coolBtn, function () { dir = dir === -1 ? 0 : -1; OS.sfx('click'); btns(); });
    slider.addEventListener('input', function () { temp = +slider.value; dir = 0; btns(); }, false);
    slider.addEventListener('change', function () { temp = +slider.value; dir = 0; btns(); }, false);
    makeParts();
    return {
      enter: function () { last = ''; if (!raf) tick(); },
      leave: function () { cancelAnimationFrame(raf); raf = null; dir = 0; btns(); }
    };
  }

  function btns() {
    heatBtn.className = 'btn btn-red' + (dir === 1 ? ' on' : '');
    coolBtn.className = 'btn btn-blue' + (dir === -1 ? ' on' : '');
  }

  function makeParts() {
    parts = [];
    var cols = 8, rows = 6, sp = 21, x0 = (L + R) / 2 - (cols - 1) * sp / 2;
    for (var r = 0; r < rows; r++) for (var c = 0; c < cols; c++) {
      var hx = x0 + c * sp, hy = B - PR - 4 - r * sp;
      parts.push({ hx: hx, hy: hy, x: hx, y: hy, vx: 0, vy: 0 });
    }
  }

  function step() {
    if (dir) {
      temp += dir * 0.35;
      if (temp > 130) { temp = 130; dir = 0; btns(); }
      if (temp < -30) { temp = -30; dir = 0; btns(); }
      slider.value = Math.round(temp);
    }
    var s = state(), surf = B - 150, i, p;
    for (i = 0; i < parts.length; i++) {
      p = parts[i];
      if (s === 'solid') {
        var amp = 0.6 + (temp + 30) / 30 * 1.6;
        var tx = p.hx + (Math.random() - 0.5) * amp * 2, ty = p.hy + (Math.random() - 0.5) * amp * 2;
        p.x += (tx - p.x) * 0.15; p.y += (ty - p.y) * 0.15; p.vx = p.vy = 0;
        continue;
      }
      var hot = s === 'gas' ? 1.3 + (temp - 100) / 30 : 0.35 + temp / 100 * 0.5;
      p.vx += (Math.random() - 0.5) * hot; p.vy += (Math.random() - 0.5) * hot;
      if (s === 'liquid') { p.vy += 0.12; p.vx *= 0.93; p.vy *= 0.93; }
      else {
        p.vx *= 0.995; p.vy *= 0.995;
        var sp = Math.sqrt(p.vx * p.vx + p.vy * p.vy), min = 2.5 + (temp - 100) / 15;
        if (sp < min && sp > 0) { p.vx *= min / sp; p.vy *= min / sp; }
      }
      p.x += p.vx; p.y += p.vy;
      var top = s === 'liquid' ? surf + PR : T + PR;
      if (p.x < L + PR) { p.x = L + PR; p.vx = Math.abs(p.vx); }
      if (p.x > R - PR) { p.x = R - PR; p.vx = -Math.abs(p.vx); }
      if (p.y > B - PR) { p.y = B - PR; p.vy = -Math.abs(p.vy); }
      if (p.y < top) { p.y += (top - p.y) * 0.2; p.vy = Math.abs(p.vy) * 0.5; }
    }
    if (s !== last) changed(s);
  }

  function changed(s) {
    var first = last === '', prev = last;
    last = s;
    info.set(TEXT[s]);
    stateEl.innerHTML = s === 'solid' ? '❄️ ثلج' : s === 'liquid' ? '💧 ماء' : '☁️ بخار';
    if (first) return;
    OS.sfx(s === 'gas' ? 'splash' : 'pop');
    var key = 'w-' + s, msg = { solid: 'تجمّد الماء وصار ثلجاً!', liquid: prev === 'gas' ? 'برد البخار وعاد ماءً!' : 'ذاب الثلج وصار ماءً!', gas: 'غلى الماء وصار بخاراً!' }[s];
    var ems = { solid: '❄️', liquid: '💧', gas: '☁️' };
    if (!OS.award(key, ems[s], msg)) OS.say(msg);
    if (OS.data.awards['w-solid'] && OS.data.awards['w-liquid'] && OS.data.awards['w-gas'])
      setTimeout(function () { OS.award('w-all', '🏆', 'عرفت حالات الماء الثلاث!'); }, 2800);
  }

  function draw() {
    var c = ctx, s = state(), i;
    c.clearRect(0, 0, 520, 420);
    // اللهب أو الثلج تحت الإناء
    if (dir === 1) {
      for (i = 0; i < 5; i++) {
        var fx = L + 40 + i * 55, fh = 30 + Math.random() * 18;
        c.fillStyle = '#ff7043'; c.beginPath(); c.moveTo(fx - 16, B + 46); c.quadraticCurveTo(fx, B + 46 - fh * 2, fx + 16, B + 46); c.fill();
        c.fillStyle = '#ffca28'; c.beginPath(); c.moveTo(fx - 8, B + 46); c.quadraticCurveTo(fx, B + 46 - fh, fx + 8, B + 46); c.fill();
      }
    }
    c.fillStyle = '#78909c'; c.fillRect(L - 20, B + 46, R - L + 40, 12);
    // الإناء
    if (s === 'liquid') { c.fillStyle = 'rgba(79,195,247,.35)'; c.fillRect(L, B - 150, R - L, 150); }
    if (s === 'solid') { c.fillStyle = 'rgba(179,229,252,.6)'; roundRect(c, parts[0].hx - 18, parts[parts.length - 1].hy - 18, 8 * 21 + 15, 6 * 21 + 15, 14); c.fill(); }
    c.strokeStyle = '#90a4ae'; c.lineWidth = 6; c.lineJoin = 'round';
    c.beginPath(); c.moveTo(L - 3, T - 10); c.lineTo(L - 3, B + 3); c.lineTo(R + 3, B + 3); c.lineTo(R + 3, T - 10); c.stroke();
    // الجزيئات
    for (i = 0; i < parts.length; i++) {
      var p = parts[i];
      c.beginPath(); c.arc(p.x, p.y, PR, 0, Math.PI * 2);
      c.fillStyle = s === 'solid' ? '#e1f5fe' : s === 'liquid' ? '#0288d1' : 'rgba(176,190,197,.85)';
      c.fill();
      c.lineWidth = 2; c.strokeStyle = s === 'solid' ? '#4fc3f7' : '#fff'; c.stroke();
    }
    thermo(c);
  }

  function thermo(c) {
    var x = 450, top = 50, bot = 330, h = bot - top;
    var f = (temp + 30) / 160; if (f < 0) f = 0; if (f > 1) f = 1;
    c.fillStyle = '#eceff1'; roundRect(c, x - 14, top - 10, 28, h + 20, 14); c.fill();
    c.strokeStyle = '#90a4ae'; c.lineWidth = 3; c.stroke();
    var col = temp < 0 ? '#29b6f6' : temp < 100 ? '#ef5350' : '#d50000';
    c.fillStyle = col; c.fillRect(x - 7, bot - h * f, 14, h * f);
    c.beginPath(); c.arc(x, bot + 22, 22, 0, Math.PI * 2); c.fill();
    c.fillStyle = '#455a64'; c.font = 'bold 15px sans-serif'; c.textAlign = 'right';
    var marks = [0, 100];
    for (var i = 0; i < marks.length; i++) {
      var y = bot - h * (marks[i] + 30) / 160;
      c.fillRect(x - 22, y - 1, 10, 3); c.fillText(marks[i] + '°', x - 26, y + 5);
    }
    c.font = 'bold 22px sans-serif'; c.textAlign = 'center';
    c.fillText(Math.round(temp) + '°', x, top - 18);
  }

  function roundRect(c, x, y, w, h, r) {
    c.beginPath(); c.moveTo(x + r, y); c.lineTo(x + w - r, y); c.quadraticCurveTo(x + w, y, x + w, y + r);
    c.lineTo(x + w, y + h - r); c.quadraticCurveTo(x + w, y + h, x + w - r, y + h); c.lineTo(x + r, y + h);
    c.quadraticCurveTo(x, y + h, x, y + h - r); c.lineTo(x, y + r); c.quadraticCurveTo(x, y, x + r, y); c.closePath();
  }

  function tick() { step(); draw(); raf = requestAnimationFrame(tick); }

  OS.register({
    id: 'water', name: 'حالات الماء', icon: '💧', color: '#0277bd', build: build, scroll: true,
    awards: [{ key: 'w-solid', e: '❄️', l: 'صنعت ثلجاً' }, { key: 'w-liquid', e: '💧', l: 'أذبت الثلج' },
      { key: 'w-gas', e: '☁️', l: 'غليت الماء' }, { key: 'w-all', e: '🏆', l: 'حالات الماء' }]
  });
})();
