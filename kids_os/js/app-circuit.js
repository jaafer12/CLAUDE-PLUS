/* الكهرباء: دائرة كهربائية بسيطة (بطارية، مفتاح، مصباح) وتجربة «موصل أم عازل». */
(function () {
  var ITEMS = [
    { p: 'key', e: '🔑', n: 'مفتاح الباب', c: true, why: 'المفتاح من المعدن، والمعدن يوصل الكهرباء.' },
    { p: 'paperclip', e: '📎', n: 'مشبك الورق', c: true, why: 'المشبك من الحديد، والحديد يوصل الكهرباء.' },
    { p: 'scissors', e: '✂️', n: 'المقص', c: true, why: 'شفرة المقص من المعدن، فتمرّ الكهرباء خلالها.' },
    { p: 'bolt', e: '🔩', n: 'البرغي', c: true, why: 'البرغي من الحديد، والحديد موصل جيد.' },
    { p: 'pencil', e: '✏️', n: 'قلم الخشب', c: false, why: 'الخشب عازل، لا يسمح للكهرباء بالمرور.' },
    { p: 'balloon', e: '🎈', n: 'البالون', c: false, why: 'البالون من المطاط، والمطاط عازل.' },
    { p: 'ruler', e: '📏', n: 'المسطرة', c: false, why: 'المسطرة من البلاستيك، والبلاستيك عازل.' },
    { p: 'leaf', e: '🍃', n: 'ورقة الشجر', c: false, why: 'ورقة الشجر الجافة لا توصل الكهرباء.' },
    { p: 'shirt', e: '👕', n: 'القميص', c: false, why: 'القماش عازل، لا تمرّ فيه الكهرباء.' }
  ];
  var svg, info, tray, modeBtns, mode = 1, closed = false, item = null, raf = null, off = 0;

  var SVG = '<svg viewBox="0 0 800 400" width="100%" height="320" style="display:block">' +
    '<defs><radialGradient id="glow"><stop offset="0" stop-color="#fff59d" stop-opacity="1"/><stop offset="1" stop-color="#fff59d" stop-opacity="0"/></radialGradient></defs>' +
    '<circle id="cGlow" cx="400" cy="45" r="110" fill="url(#glow)" opacity="0"/>' +
    '<path d="M120,200 L120,80 L680,80 L680,330 L120,330 Z" fill="none" stroke="#475569" stroke-width="9" stroke-linejoin="round"/>' +
    '<rect x="236" y="318" width="68" height="24" fill="#fff"/>' +
    '<rect id="cGapCover" x="476" y="318" width="88" height="24" fill="#fff"/>' +
    '<path id="cFlow" d="M120,200 L120,80 L680,80 L680,330 L120,330 Z" fill="none" stroke="#f59e0b" stroke-width="6" stroke-linecap="round" stroke-dasharray="3 24" opacity="0"/>' +
    // المصباح
    '<rect x="382" y="66" width="36" height="30" rx="7" fill="#94a3b8"/>' +
    '<circle id="cBulb" cx="400" cy="40" r="34" fill="#f1f5f9" stroke="#94a3b8" stroke-width="4"/>' +
    '<path id="cFil" d="M386,52 Q393,26 400,52 Q407,26 414,52" fill="none" stroke="#8d6e63" stroke-width="3"/>' +
    '<text x="400" y="128" font-size="22" text-anchor="middle" fill="#8a7a62">مصباح</text>' +
    // البطارية
    '<rect x="110" y="148" width="20" height="12" rx="3" fill="#94a3b8"/>' +
    '<rect x="92" y="158" width="56" height="44" rx="10" fill="#f59e0b"/>' +
    '<rect x="92" y="198" width="56" height="66" rx="10" fill="#334155"/>' +
    '<text x="120" y="190" font-size="28" text-anchor="middle" fill="#fff" font-weight="bold">+</text>' +
    '<text x="120" y="245" font-size="30" text-anchor="middle" fill="#fff" font-weight="bold">−</text>' +
    '<text x="190" y="215" font-size="22" text-anchor="middle" fill="#8a7a62">بطارية</text>' +
    // المفتاح
    '<g id="cSwitch">' +
    '<rect x="200" y="270" width="140" height="110" fill="#fff" opacity="0"/>' +
    '<circle cx="236" cy="330" r="9" fill="#334155"/><circle cx="304" cy="330" r="9" fill="#334155"/>' +
    '<line id="cLever" x1="236" y1="330" x2="308" y2="330" stroke="#ef4444" stroke-width="10" stroke-linecap="round"/>' +
    '<text x="270" y="385" font-size="22" text-anchor="middle" fill="#8a7a62">المفتاح (اضغط)</text></g>' +
    // فراغ الاختبار
    '<g id="cGap"><circle cx="476" cy="330" r="9" fill="#334155"/><circle cx="564" cy="330" r="9" fill="#334155"/>' +
    '<rect id="cSlot" x="484" y="296" width="72" height="68" rx="12" fill="none" stroke="#90a4ae" stroke-width="3" stroke-dasharray="8 6"/>' +
    '<text id="cObj" x="520" y="350" font-size="52" text-anchor="middle">?</text>' +
    '<image id="cImg" x="486" y="298" width="68" height="64" preserveAspectRatio="xMidYMid slice" style="display:none"/>' +
    '<text x="520" y="392" font-size="20" text-anchor="middle" fill="#8a7a62">ضع شيئاً هنا</text></g>' +
    '</svg>';

  function $(id) { return svg.querySelector('#' + id); }

  function build(body) {
    var wrap = OS.el('<div></div>');
    info = OS.info('');
    var panel = OS.el('<div class="panel" style="padding:0"></div>');
    panel.innerHTML = SVG; svg = panel.firstChild;
    modeBtns = OS.el('<div class="row"></div>');
    tray = OS.el('<div class="tray"></div>');
    wrap.appendChild(info); wrap.appendChild(panel); wrap.appendChild(modeBtns); wrap.appendChild(tray);
    body.appendChild(wrap);
    OS.tap($('cSwitch'), function () { if (mode === 1) { closed = !closed; update(true); } });
    var b1 = OS.el('<button class="btn btn-orange">شغّل المصباح</button>');
    var b2 = OS.el('<button class="btn btn-teal">موصل أم عازل؟</button>');
    OS.tap(b1, function () { setMode(1); }); OS.tap(b2, function () { setMode(2); });
    modeBtns.appendChild(b1); modeBtns.appendChild(b2);
    setMode(1);
    return { enter: function () { loop();  }, leave: function () { cancelAnimationFrame(raf); raf = null; } };
  }

  function setMode(m) {
    mode = m; item = null;     modeBtns.childNodes[0].className = 'btn btn-orange' + (m === 1 ? ' on' : '');
    modeBtns.childNodes[1].className = 'btn btn-teal' + (m === 2 ? ' on' : '');
    $('cGap').style.display = m === 2 ? '' : 'none';
    $('cGapCover').style.display = m === 2 ? '' : 'none';
    tray.innerHTML = '';
    if (m === 1) {
      closed = false;
      info.set('اضغط على <b>المفتاح</b> لتُغلق الدائرة فيضيء المصباح!<br>لا تلمس كهرباء البيت أبداً.');
    } else {
      closed = true;
      info.set('ضع شيئاً في الفراغ: هل يضيء المصباح؟ <b>الموصل</b> يُضيئه، و<b>العازل</b> لا.');
      var done = OS.data.circuit || {};
      OS.each(ITEMS, function (it, i) {
        var n = OS.el('<div class="item' + (done[i] ? ' done' : '') + '"><span class="em">' + OS.pic(it.p, it.e) + '</span>' + it.n + '</div>');
        OS.tap(n, function () { guess(i, n); });
        tray.appendChild(n);
      });
    }
    update(false);
  }

  function lit() { return closed && (mode === 1 || (item !== null && ITEMS[item].c)); }

  function update(feedback) {
    $('cLever').setAttribute('transform', closed ? '' : 'rotate(-35 236 330)');
    var photo = item !== null && OS.photos[ITEMS[item].p];
    $('cObj').textContent = item === null ? '?' : photo ? '' : ITEMS[item].e;
    $('cImg').style.display = photo ? '' : 'none';
    if (photo) $('cImg').setAttributeNS('http://www.w3.org/1999/xlink', 'href', OS.photoUrl(ITEMS[item].p));
    var on = lit();
    $('cBulb').setAttribute('fill', on ? '#fde68a' : '#f1f5f9');
    $('cBulb').setAttribute('stroke', on ? '#f59e0b' : '#94a3b8');
    $('cFil').setAttribute('stroke', on ? '#ff6f00' : '#8d6e63');
    $('cGlow').setAttribute('opacity', on ? '1' : '0');
    $('cFlow').setAttribute('opacity', on ? '1' : '0');
    if (feedback && mode === 1) {
      if (on) { OS.award('c-first', '💡', 'أضأت المصباح! الدائرة مغلقة'); }
    }
  }

  function guess(i, node) {
    var it = ITEMS[i];
        OS.ask(OS.pic(it.p, it.e, 'big') + '<br>هل سيضيء المصباح مع ' + it.n + '؟', [
      { label: 'نعم يضيء', cls: 'btn-orange', fn: function () { place(i, node, true); } },
      { label: 'لا يضيء', cls: 'btn-blue', fn: function () { place(i, node, false); } }
    ]);
  }

  function place(i, node, said) {
    item = i; update(false);
    var it = ITEMS[i], right = said === it.c;
    var done = OS.data.circuit || (OS.data.circuit = {});
    setTimeout(function () {
      if (right) {
                if (!done[i]) { done[i] = 1; OS.addStars(1); node.className = 'item done'; }
        OS.ok('صحيح! ' + it.why, 3200);
      } else {
                OS.hint('ليس تماماً. ' + it.why, 3600);
      }
      var all = true; for (var k = 0; k < ITEMS.length; k++) if (!done[k]) all = false;
      if (all) setTimeout(function () { OS.award('c-all', '🔌', 'عرفت كل الموصلات والعوازل!'); }, 3700);
    }, 500);
  }

  function loop() {
    if (raf) return;
    var flow = $('cFlow');
    (function tick() {
      off -= 1.2;
      if (lit()) flow.setAttribute('stroke-dashoffset', off);
      raf = requestAnimationFrame(tick);
    })();
  }

  OS.register({
    id: 'circuit', name: 'الكهرباء', icon: 'bulb', color: '#f59e0b', shade: '#b45309', build: build, scroll: true,
    awards: [{ key: 'c-first', e: '💡', l: 'أضأت المصباح' }, { key: 'c-all', e: '🔌', l: 'موصل أم عازل' }]
  });
})();
