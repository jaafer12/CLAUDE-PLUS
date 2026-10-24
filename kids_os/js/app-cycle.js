/* دورة الماء: الشمس تبخّر ماء البحر ← غيمة ← مطر ← نهر يعود إلى البحر. */
(function () {
  var W = 900, H = 420, SUN = { x: 110, y: 80 }, CLOUD = { x: 600, y: 95 };
  var cv, ctx, info, raf = null, step = 0, fill = 0, parts = [], t = 0, phaseEnd = 0, label = '';

  var TEXT = [
    'اضغط على <b>الشمس</b> لتسخّن ماء البحر.',
    'الغيمة <b>امتلأت</b> بقطرات الماء! اضغط عليها.',
    '<b>هطول</b>: الماء ينزل مطراً على الجبل.',
    '<b>جريان</b>: المطر يجري في النهر عائداً إلى البحر.'
  ];

  function build(body) {
    var wrap = OS.el('<div></div>');
    info = OS.info(TEXT[0]);
    var panel = OS.el('<div class="panel" style="padding:6px"></div>');
    cv = document.createElement('canvas'); cv.width = W; cv.height = H; cv.className = 'stage-cv';
    ctx = cv.getContext('2d');
    panel.appendChild(cv);
    wrap.appendChild(info); wrap.appendChild(panel);
    body.appendChild(wrap);
    cv.addEventListener('touchstart', tapped, false); cv.addEventListener('mousedown', tapped, false);
    return {
      enter: function () { loop();  },
      leave: function () { cancelAnimationFrame(raf); raf = null; }
    };
  }

  function near(p, o, r) { var dx = p.x - o.x, dy = p.y - o.y; return dx * dx + dy * dy < r * r; }

  function tapped(e) {
    e.preventDefault();
    var p = OS.canvasPoint(cv, e);
    if (step === 0 && fill < 3 && near(p, SUN, 90)) {
            for (var i = 0; i < 14; i++) parts.push({ k: 'v', x: 40 + Math.random() * 340, y: 340 + Math.random() * 30, life: 0 });
      label = 'تبخّر';
      fill++;
      if (fill === 3) setTimeout(function () { step = 1; info.set(TEXT[1]); label = 'تكاثف';  }, 1600);
    } else if (step === 1 && near(p, CLOUD, 110)) {
      step = 2; info.set(TEXT[2]); label = 'هطول'; phaseEnd = t + 150; 
    }
  }

  function update() {
    t++;
    var i, q;
    for (i = parts.length - 1; i >= 0; i--) {
      q = parts[i]; q.life++;
      if (q.k === 'v') { q.y -= 1.6; q.x += (CLOUD.x - q.x) * 0.012; if (q.y < CLOUD.y + 20) parts.splice(i, 1); }
      else if (q.k === 'r') { q.y += 7; if (q.y > 300) parts.splice(i, 1); }
    }
    if (step === 2) {
      for (i = 0; i < 3; i++) parts.push({ k: 'r', x: CLOUD.x - 90 + Math.random() * 180, y: CLOUD.y + 30 });
      if (t > phaseEnd) { step = 3; info.set(TEXT[3]); label = 'جريان'; phaseEnd = t + 200;  }
    } else if (step === 3 && t > phaseEnd) {
      step = 0; fill = 0; label = '';
      info.set('عاد الماء إلى البحر… وتبدأ <b>دورة الماء</b> من جديد! ' + TEXT[0]);
            OS.award('cyc-all', '🔄', 'أكملت دورة الماء كلها!');
    }
  }

  function cloud(c, x, y, s, col) {
    c.fillStyle = col; c.beginPath();
    c.arc(x - 60 * s, y + 10 * s, 40 * s, 0, Math.PI * 2); c.arc(x, y - 10 * s, 55 * s, 0, Math.PI * 2);
    c.arc(x + 60 * s, y + 10 * s, 40 * s, 0, Math.PI * 2); c.fill();
  }

  function draw() {
    var c = ctx, i;
    c.fillStyle = '#81d4fa'; c.fillRect(0, 0, W, H);
    // الشمس
    c.fillStyle = 'rgba(255,214,0,.3)'; c.beginPath(); c.arc(SUN.x, SUN.y, 62 + Math.sin(t / 10) * 4, 0, Math.PI * 2); c.fill();
    c.fillStyle = '#ffd600'; c.beginPath(); c.arc(SUN.x, SUN.y, 44, 0, Math.PI * 2); c.fill();
    // الجبل والنهر
    c.fillStyle = '#8d6e63'; c.beginPath(); c.moveTo(500, H); c.lineTo(740, 170); c.lineTo(W + 40, H); c.closePath(); c.fill();
    c.fillStyle = '#fff'; c.beginPath(); c.moveTo(700, 220); c.lineTo(740, 170); c.lineTo(780, 220); c.closePath(); c.fill();
    c.fillStyle = '#66bb6a'; c.fillRect(380, 360, W - 380, H - 360);
    c.strokeStyle = '#29b6f6'; c.lineWidth = 16; c.lineCap = 'round';
    c.beginPath(); c.moveTo(700, 300); c.quadraticCurveTo(600, 380, 380, 380); c.stroke();
    if (step === 3) {
      if (c.setLineDash) c.setLineDash([10, 22]);
      c.lineDashOffset = -t * 2; c.strokeStyle = '#e1f5fe'; c.lineWidth = 6;
      c.beginPath(); c.moveTo(700, 300); c.quadraticCurveTo(600, 380, 380, 380); c.stroke();
      if (c.setLineDash) c.setLineDash([]);
    }
    // البحر
    c.fillStyle = '#0288d1'; c.fillRect(0, 330, 420, H - 330);
    c.fillStyle = 'rgba(255,255,255,.4)';
    for (i = 0; i < 6; i++) { c.beginPath(); c.arc(30 + i * 70 + Math.sin(t / 20 + i) * 6, 340, 14, Math.PI, 0); c.fill(); }
    // الغيمة تكبر وتغمق كلما امتلأت
    var s = 0.6 + Math.min(fill, 3) * 0.17, shade = step >= 1 ? '#90a4ae' : ['#ffffff', '#f5f5f5', '#e0e0e0', '#cfd8dc'][Math.min(fill, 3)];
    cloud(c, CLOUD.x, CLOUD.y, s, shade);
    // البخار والمطر
    for (i = 0; i < parts.length; i++) {
      var q = parts[i];
      if (q.k === 'v') { c.fillStyle = 'rgba(255,255,255,.75)'; c.beginPath(); c.arc(q.x, q.y, 6, 0, Math.PI * 2); c.fill(); }
      else { c.strokeStyle = '#1565c0'; c.lineWidth = 3; c.beginPath(); c.moveTo(q.x, q.y); c.lineTo(q.x - 2, q.y + 12); c.stroke(); }
    }
    // الإرشاد والاسم العلمي للمرحلة
    c.font = 'bold 26px sans-serif'; c.textAlign = 'center'; c.fillStyle = '#263238';
    // حلقة نابضة حول ما يجب أن يضغط عليه الطفل
    var target = step === 0 ? SUN : step === 1 ? CLOUD : null;
    if (target) {
      c.strokeStyle = 'rgba(245,158,11,' + (0.35 + 0.35 * Math.sin(t / 8)) + ')'; c.lineWidth = 8;
      c.beginPath(); c.arc(target.x, target.y, step === 0 ? 70 : 105, 0, Math.PI * 2); c.stroke();
    }
    if (label) {
      c.fillStyle = 'rgba(255,255,255,.85)'; c.fillRect(W / 2 - 120, 12, 240, 46);
      c.fillStyle = '#01579b'; c.font = 'bold 30px sans-serif'; c.fillText(label, W / 2, 46);
    }
  }

  function loop() {
    if (raf) return;
    (function tick() { update(); draw(); raf = requestAnimationFrame(tick); })();
  }

  OS.register({
    id: 'cycle', name: 'دورة الماء', icon: 'cloud', color: '#3b82f6', shade: '#1d4ed8', build: build, scroll: true,
    awards: [{ key: 'cyc-all', e: '🔄', l: 'دورة الماء' }]
  });
})();
