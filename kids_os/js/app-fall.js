/* السقوط: الكرة والريشة مع الهواء وبدونه (مثل القمر). */
(function () {
  var W = 600, H = 440, TOP = 70, FLOOR = 400;
  var cv, ctx, info, airBtn, moonBtn, air = true, raf = null, run = null;
  var ball = { x: 200, y: TOP }, feather = { x: 400, y: TOP };

  function build(body) {
    var wrap = OS.el('<div></div>');
    info = OS.info('نُفلت <b>كرة</b> و<b>ريشة</b> معاً. أيّهما تصل إلى الأرض أولاً؟');
    var panel = OS.el('<div class="panel row" style="padding:6px"></div>');
    cv = document.createElement('canvas'); cv.width = W; cv.height = H; cv.className = 'stage-cv'; cv.style.width = '560px';
    ctx = cv.getContext('2d');
    var side = OS.el('<div style="width:300px;text-align:center"></div>');
    airBtn = OS.el('<button class="btn btn-blue" style="width:260px">مع الهواء</button>');
    moonBtn = OS.el('<button class="btn btn-teal" style="width:260px">بلا هواء (القمر)</button>');
    var drop = OS.el('<button class="btn btn-orange" style="width:260px;font-size:28px">أفلِت!</button>');
    OS.tap(airBtn, function () { setAir(true); }); OS.tap(moonBtn, function () { setAir(false); }); OS.tap(drop, ask);
    side.appendChild(airBtn); side.appendChild(moonBtn); side.appendChild(drop);
    panel.appendChild(cv); panel.appendChild(side);
    wrap.appendChild(info); wrap.appendChild(panel);
    body.appendChild(wrap);
    setAir(true, true);
    return {
      enter: function () { reset(); loop();  },
      leave: function () { cancelAnimationFrame(raf); raf = null; run = null; }
    };
  }

  function setAir(a, quiet) {
    air = a; run = null; reset();
    airBtn.className = 'btn btn-blue' + (a ? ' on' : ''); moonBtn.className = 'btn btn-teal' + (a ? '' : ' on');
  }
  function reset() { ball.y = feather.y = TOP; ball.v = feather.v = 0; feather.x = 400; }

  function ask() {
    if (run) return;
    reset();
    OS.ask('أيّهما تصل إلى الأرض أولاً' + (air ? '' : ' على القمر') + '؟', [
      { label: 'الكرة', cls: 'btn-orange', fn: function () { go('ball'); } },
      { label: 'الريشة', cls: 'btn-teal', fn: function () { go('feather'); } },
      { label: 'معاً', cls: 'btn-blue', fn: function () { go('same'); } }
    ]);
  }

  function go(guess) { run = { guess: guess, t: 0, done: false }; }

  function step() {
    if (!run || run.done) return;
    run.t++;
    var g = 0.35;
    if (ball.y < FLOOR) { ball.v += g; ball.y = Math.min(FLOOR, ball.y + ball.v); }
    if (feather.y < FLOOR) {
      if (air) { feather.v = Math.min(feather.v + 0.05, 1.3); feather.x = 400 + Math.sin(run.t / 18) * 40; }
      else feather.v += g;
      feather.y = Math.min(FLOOR, feather.y + feather.v);
    }
    if (ball.y >= FLOOR && feather.y >= FLOOR) finish();
  }

  function finish() {
    run.done = true;
    var answer = air ? 'ball' : 'same', right = run.guess === answer;
    var why = air ? 'الهواء يدفع الريشة الخفيفة العريضة فتسقط ببطء، والكرة تشقّ الهواء بسرعة.'
      : 'بلا هواء تسقط كل الأشياء بالسرعة نفسها، الثقيلة والخفيفة!';
    setTimeout(function () {
      if (right) {
                if (!OS.award(air ? 'fall-air' : 'fall-moon', air ? '🏀' : '🌙', 'صحيح! ' + why)) OS.ok('صحيح! ' + why, 3400);
      } else { OS.hint('انظر! ' + why, 3600); }
      run = null;
    }, 400);
  }

  function obj(id, emoji, x, y) {
    var im = OS.photo(id), r = 34, c = ctx;
    if (im) {
      c.save(); c.beginPath(); c.arc(x, y, r, 0, Math.PI * 2); c.clip();
      c.drawImage(im, x - r, y - r, 2 * r, 2 * r); c.restore();
      c.strokeStyle = '#fff'; c.lineWidth = 4; c.beginPath(); c.arc(x, y, r, 0, Math.PI * 2); c.stroke();
    } else { c.font = '56px sans-serif'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(emoji, x, y); }
  }

  // ريشة مرسومة: ساق وزغب على الجانبين
  function drawFeather(x, y, tilt) {
    var c = ctx;
    c.save(); c.translate(x, y); c.rotate(-0.5 + tilt);
    c.fillStyle = '#fafafa'; c.strokeStyle = '#90a4ae'; c.lineWidth = 2;
    c.beginPath(); c.moveTo(0, -48);
    c.quadraticCurveTo(26, -20, 10, 40); c.lineTo(-2, 40);
    c.quadraticCurveTo(-24, -10, 0, -48); c.closePath(); c.fill(); c.stroke();
    c.strokeStyle = '#b0bec5'; c.lineWidth = 1.5;
    for (var i = -36; i < 34; i += 8) { c.beginPath(); c.moveTo(3, i); c.lineTo(14 - Math.abs(i) / 6, i - 6); c.moveTo(3, i); c.lineTo(-10 + Math.abs(i) / 8, i - 6); c.stroke(); }
    c.strokeStyle = '#78909c'; c.lineWidth = 3;
    c.beginPath(); c.moveTo(0, -46); c.quadraticCurveTo(6, 0, 4, 56); c.stroke();
    c.restore();
  }

  function draw() {
    var c = ctx;
    c.fillStyle = air ? '#b3e5fc' : '#0d1b4c'; c.fillRect(0, 0, W, H);
    if (!air) { c.fillStyle = '#fff'; for (var i = 0; i < 30; i++) c.fillRect((i * 97) % W, (i * 53) % 300, 2, 2); }
    c.fillStyle = air ? '#8bc34a' : '#9e9e9e'; c.fillRect(0, FLOOR + 34, W, H - FLOOR - 34);
    // الرفّ الذي نُفلت منه
    c.fillStyle = '#795548'; c.fillRect(140, TOP - 44, 320, 10);
    obj('basketball', '🏀', ball.x, ball.y);
    drawFeather(feather.x, feather.y, run && air ? Math.sin(run.t / 18) * 0.5 : 0);
    c.fillStyle = air ? '#37474f' : '#fff'; c.font = 'bold 20px sans-serif'; c.textAlign = 'center'; c.textBaseline = 'alphabetic';
    c.fillText('الكرة', 200, TOP - 52);
    c.fillText('الريشة', 400, TOP - 52);
  }

  function loop() {
    if (raf) return;
    (function tick() { step(); draw(); raf = requestAnimationFrame(tick); })();
  }

  OS.register({
    id: 'fall', name: 'السقوط', icon: 'fall', color: '#f97316', shade: '#c2410c', build: build, scroll: true,
    awards: [{ key: 'fall-air', e: '🏀', l: 'الكرة والريشة' }, { key: 'fall-moon', e: '🌙', l: 'السقوط على القمر' }]
  });
})();
