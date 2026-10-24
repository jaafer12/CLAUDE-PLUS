/* الضوء والظل: حرّك الشمس فيتغيّر طول الظل واتجاهه. */
(function () {
  var W = 900, H = 400, G = 330;          // أبعاد اللوحة وخط الأرض
  var OX = 450, OT = 190;                 // مكان الشجرة وارتفاع قمتها
  var cv, ctx, info, sun = { x: 220, y: 90 }, drag = false, raf = null, dirty = true;

  function build(body) {
    var wrap = OS.el('<div></div>');
    info = OS.info('حرّك <b>الشمس</b> بإصبعك وانظر إلى <b>الظل</b>: متى يصير طويلاً؟ ومتى يصير قصيراً؟');
    var panel = OS.el('<div class="panel" style="padding:6px"></div>');
    cv = document.createElement('canvas'); cv.width = W; cv.height = H; cv.className = 'stage-cv';
    ctx = cv.getContext('2d');
    panel.appendChild(cv);
    wrap.appendChild(info); wrap.appendChild(panel);
    body.appendChild(wrap);
    cv.addEventListener('touchstart', down, false); cv.addEventListener('mousedown', down, false);
    cv.addEventListener('touchmove', move, false); cv.addEventListener('mousemove', move, false);
    document.addEventListener('touchend', up, false); document.addEventListener('mouseup', up, false);
    return {
      enter: function () { dirty = true; loop(); OS.say(info.lastChild.innerHTML.replace(/<[^>]+>/g, ' ')); },
      leave: function () { cancelAnimationFrame(raf); raf = null; }
    };
  }

  function down(e) { e.preventDefault(); drag = true; setSun(e); }
  function move(e) { if (!drag) return; e.preventDefault(); setSun(e); }
  function up() { if (drag) { drag = false; judge(); } }
  function setSun(e) {
    var p = OS.canvasPoint(cv, e);
    sun.x = Math.max(40, Math.min(W - 40, p.x));
    sun.y = Math.max(40, Math.min(G - 60, p.y));
    dirty = true;
  }

  // طرف الظل على الأرض: امتداد الخط من الشمس عبر قمة الشجرة
  function tip() {
    if (sun.y >= OT - 5) return sun.x < OX ? W + 200 : -200;
    return sun.x + (OX - sun.x) * (G - sun.y) / (OT - sun.y);
  }

  function judge() {
    var len = Math.abs(tip() - OX);
    if (len > 320) { OS.sfx('ding'); if (!OS.award('sh-long', '🌅', 'الشمس منخفضة فصار الظل طويلاً جداً!')) OS.say('الشمس منخفضة، الظل طويل'); }
    else if (len < 50) { OS.sfx('ding'); if (!OS.award('sh-short', '☀️', 'الشمس فوق الشجرة فصار الظل قصيراً جداً!')) OS.say('الشمس عالية، الظل قصير'); }
    info.set(len > 200 ? '🌅 الشمس <b>منخفضة</b> (صباحاً أو مساءً) فالظل <b>طويل</b>.' :
      len < 80 ? '☀️ الشمس <b>عالية</b> (وقت الظهر) فالظل <b>قصير</b>.' :
      'الظل يكون دائماً في <b>الجهة المعاكسة</b> للشمس.');
  }

  function draw() {
    var c = ctx, low = 1 - (sun.y - 40) / (G - 100); // 1 = الشمس عالية
    // السماء: زرقاء في الظهر، برتقالية حين تنخفض الشمس
    var r = Math.round(255 - 150 * low), g = Math.round(170 + 40 * low), b = Math.round(120 + 130 * low);
    c.fillStyle = 'rgb(' + r + ',' + g + ',' + b + ')'; c.fillRect(0, 0, W, H);
    c.fillStyle = '#7cb342'; c.fillRect(0, G, W, H - G);
    // الظل
    var t = tip(), half = 12;
    c.fillStyle = 'rgba(0,0,0,.35)';
    c.beginPath(); c.moveTo(OX - half, G + 4); c.lineTo(OX + half, G + 4);
    c.lineTo(t, G + 18); c.lineTo(t, G + 8); c.closePath(); c.fill();
    c.beginPath();
    var cx = OX + (t - OX) * 0.78, rx = Math.min(Math.abs(t - OX) * 0.3 + 30, 140);
    c.save(); c.translate(cx, G + 10); c.scale(1, 0.18); c.arc(0, 0, rx, 0, Math.PI * 2); c.restore(); c.fill();
    // الشجرة
    c.fillStyle = '#6d4c41'; c.fillRect(OX - 12, OT + 50, 24, G - OT - 50);
    c.fillStyle = '#2e7d32'; c.beginPath(); c.arc(OX, OT + 42, 46, 0, Math.PI * 2); c.fill();
    c.beginPath(); c.arc(OX - 30, OT + 60, 30, 0, Math.PI * 2); c.arc(OX + 30, OT + 60, 30, 0, Math.PI * 2); c.fill();
    // الأشعة والشمس
    c.strokeStyle = 'rgba(255,214,0,.35)'; c.lineWidth = 3;
    c.beginPath(); c.moveTo(sun.x, sun.y); c.lineTo(OX, OT); c.stroke();
    c.fillStyle = '#ffd600'; c.beginPath(); c.arc(sun.x, sun.y, 34, 0, Math.PI * 2); c.fill();
    c.fillStyle = 'rgba(255,214,0,.3)'; c.beginPath(); c.arc(sun.x, sun.y, 52, 0, Math.PI * 2); c.fill();
    c.fillStyle = '#5d4037'; c.font = 'bold 22px sans-serif'; c.textAlign = 'center';
    c.fillText('☝️ اسحب الشمس', Math.max(110, Math.min(W - 110, sun.x)), sun.y + 80 > G ? sun.y - 60 : sun.y + 80);
  }

  function loop() {
    if (raf) return;
    (function tick() { if (dirty) { draw(); dirty = false; } raf = requestAnimationFrame(tick); })();
  }

  OS.register({
    id: 'shadow', name: 'الضوء والظل', icon: '🌓', color: '#6a1b9a', build: build, scroll: true,
    awards: [{ key: 'sh-long', e: '🌅', l: 'ظل طويل' }, { key: 'sh-short', e: '☀️', l: 'ظل قصير' }]
  });
})();
