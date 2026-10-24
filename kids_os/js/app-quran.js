/* القرآن الكريم: قصار السور للأطفال — قراءة، حفظ بإخفاء الكلمات، وترتيب الآيات.
   النص من js/quran.js (يُولَّد من مصدر موثّق، انظر tools/data/QURAN_SOURCE.md)؛ لا تُكتب الآيات هنا. */
(function () {
  // معنى مبسّط لكل سورة (للتعريف فقط؛ يُستحسن أن يشرحه الأهل)
  var MEANING = {
    1: 'نحمد الله ربّ العالمين، ونعبده وحده، ونسأله أن يهدينا إلى الطريق المستقيم.',
    103: 'يُقسم الله بالزمن أن الإنسان في خسارة، إلا الذين آمنوا وعملوا الصالحات وأوصى بعضهم بعضاً بالحق والصبر.',
    105: 'قصة أصحاب الفيل الذين أرادوا هدم الكعبة، فأرسل الله عليهم طيراً أبابيل.',
    106: 'يذكّر الله قريشاً بنعمته عليهم في رحلتي الشتاء والصيف، فقد أطعمهم وآمنهم، فليعبدوا ربّ هذا البيت.',
    107: 'تذمّ السورة من لا يرحم اليتيم ولا يُطعم المسكين، ومن يسهو عن صلاته ويمنع العون عن الناس.',
    108: 'أعطى الله النبيَّ صلى الله عليه وسلم الكوثر، وهو نهر في الجنة، فليصلِّ لربه ويذبح شكراً له.',
    109: 'نعبد الله وحده، ولا نعبد ما يعبده غيرنا.',
    110: 'إذا جاء نصر الله والفتح ودخل الناس في الإسلام، فسبّح بحمد ربك واستغفره.',
    111: 'تخبر عن أبي لهب وامرأته اللذين آذيا النبي صلى الله عليه وسلم، وعن جزائهما.',
    112: 'الله واحد أحد، لم يلد ولم يولد، وليس له شبيه.',
    113: 'نستعيذ بالله ربّ الفلق من شرّ ما خلق، ومن شرّ الظلام والسحر والحسد.',
    114: 'نستعيذ بالله ربّ الناس من وسوسة الشيطان.'
  };
  var DIG = '٠١٢٣٤٥٦٧٨٩';
  function ar(n) { return String(n).replace(/[0-9]/g, function (d) { return DIG[+d]; }); }

  var box, sura = 0, mode = 'read', reveal = [], order = [], next = 0;

  function done() { return OS.data.quran || (OS.data.quran = {}); }

  function build(body) { box = OS.el('<div></div>'); body.appendChild(box); return { enter: list }; }

  // ---------- قائمة السور ----------
  function list() {
    sura = 0;
    var h = '<div class="info">اختر سورة لتقرأها وتحفظها. السور التي رتّبت آياتها تصير خضراء.</div><div class="sura-list">';
    OS.each(OS.QURAN_ORDER, function (n) {
      var s = OS.QURAN[n];
      h += '<div class="sura' + (done()[n] ? ' done' : '') + '" data-n="' + n + '"><span class="no">' + ar(n) + '</span>' +
        '<div class="sn">' + s.name + '</div><div class="ay">' + ar(s.verses.length) + ' آيات</div></div>';
    });
    box.innerHTML = h + '</div><div class="qnote">نص المصحف برواية حفص من موسوعة القرآن الكريم (quranenc.com).</div>';
    OS.each(box.querySelectorAll('.sura'), function (n) { OS.tap(n, function () { openSura(+n.getAttribute('data-n')); }); });
  }

  // ---------- السورة ----------
  function openSura(n) { sura = n; mode = 'read'; draw(); box.parentNode.scrollTop = 0; }

  function words(text) { return text.split(' '); }

  function draw() {
    var s = OS.QURAN[sura];
    var h = '<div class="row" style="margin-top:12px">' +
      '<button class="btn btn-white" data-a="list">كل السور</button>' +
      '<button class="btn ' + (mode === 'read' ? 'btn-green' : 'btn-white') + '" data-a="read">اقرأ</button>' +
      '<button class="btn ' + (mode === 'hide' ? 'btn-green' : 'btn-white') + '" data-a="hide">احفظ</button>' +
      '<button class="btn ' + (mode === 'order' ? 'btn-green' : 'btn-white') + '" data-a="order">رتّب الآيات</button></div>';
    h += '<div class="title2" style="font-family:\'Amiri Quran\',serif;font-size:40px;font-weight:normal;color:#065f46">سورة ' + s.name + '</div>';
    if (mode === 'order') h += orderHtml(s);
    else {
      if (mode === 'hide') h += '<div class="info">اضغط على الآية لتظهر الكلمة التالية. حاول أن تتذكّرها قبل أن تضغط!</div>';
      h += '<div class="mushaf">' + (sura !== 1 ? '<div class="basmala">' + OS.QURAN[1].verses[0] + '</div>' : '');
      OS.each(s.verses, function (v, i) {
        var ws = words(v), shown = mode === 'hide' ? reveal[i] : ws.length, t = '';
        OS.each(ws, function (w, k) { t += '<span class="w' + (k >= shown ? ' hid' : '') + '">' + w + '</span> '; });
        h += '<div class="ayah" data-i="' + i + '">' + t + '<span class="num">' + ar(i + 1) + '</span></div>';
      });
      h += '</div><div class="meaning"><b>المعنى المبسّط:</b> ' + MEANING[sura] + '</div>';
    }
    box.innerHTML = h;
    OS.each(box.querySelectorAll('[data-a]'), function (b) { OS.tap(b, function () { act(b.getAttribute('data-a')); }); });
    OS.each(box.querySelectorAll('.ayah'), function (a) { OS.tap(a, function () { ayahTap(+a.getAttribute('data-i'), a); }); });
    OS.each(box.querySelectorAll('.order-card'), function (c) { OS.tap(c, function () { pick(+c.getAttribute('data-i'), c); }); });
  }

  function act(a) {
    if (a === 'list') return list();
    mode = a;
    var s = OS.QURAN[sura];
    if (a === 'hide') { reveal = []; OS.each(s.verses, function () { reveal.push(1); }); }
    if (a === 'order') { order = OS.shuffle(s.verses.map(function (v, i) { return i; })); next = 0; }
    draw();
  }

  function ayahTap(i, node) {
    if (mode === 'read') {
      OS.each(box.querySelectorAll('.ayah'), function (a) { a.className = 'ayah'; });
      node.className = 'ayah cur';
      return;
    }
    // وضع الحفظ: أظهر الكلمة التالية من هذه الآية
    var ws = node.querySelectorAll('.w');
    if (reveal[i] < ws.length) { ws[reveal[i]].className = 'w'; reveal[i]++; }
    var all = true;
    OS.each(OS.QURAN[sura].verses, function (v, k) { if (reveal[k] < words(v).length) all = false; });
    if (all) OS.ok('ما شاء الله! أكملت السورة، أعدها مرة أخرى من حفظك.', 3000);
  }

  // ---------- ترتيب الآيات ----------
  function orderHtml(s) {
    var h = '<div class="info">اضغط على الآيات <b>بالترتيب</b>: الأولى ثم الثانية…</div>';
    OS.each(order, function (i) {
      h += '<div class="order-card' + (i < next ? ' ok' : '') + '" data-i="' + i + '">' + (i < next ? '<b>' + ar(i + 1) + '</b> ' : '') + s.verses[i] + '</div>';
    });
    return h;
  }
  function pick(i, card) {
    if (i < next) return;
    if (i === next) {
      next++;
      card.className = 'order-card ok';
      card.innerHTML = '<b>' + ar(i + 1) + '</b> ' + OS.QURAN[sura].verses[i];
      if (next === OS.QURAN[sura].verses.length) finish();
    } else {
      card.className = 'order-card'; void card.offsetWidth; card.className = 'order-card bad';
      OS.hint('ليست هذه. ابحث عن الآية رقم ' + ar(next + 1), 1800);
    }
  }
  function finish() {
    var d = done(), first = !d[sura];
    d[sura] = 1; OS.save();
    if (first) OS.addStars(1);
    OS.ok('أحسنت! رتّبت آيات سورة ' + OS.QURAN[sura].name + ' كلها.', 3000);
    // نعرض الآيات بترتيب المصحف بعد الإكمال
    setTimeout(function () { if (mode === 'order') { order.sort(function (a, b) { return a - b; }); draw(); } }, 900);
    var n = 0; for (var k in d) n++;
    if (n >= 3) setTimeout(function () { OS.award('qr-3', '', 'رتّبت ثلاث سور!'); }, 3100);
    if (n >= OS.QURAN_ORDER.length) setTimeout(function () { OS.award('qr-all', '', 'رتّبت كل السور! بارك الله فيك'); }, 6200);
  }

  OS.register({
    id: 'quran', name: 'القرآن الكريم', icon: 'quran', color: '#10b981', shade: '#047857', build: build, scroll: true,
    awards: [{ key: 'qr-3', e: '', l: 'ثلاث سور' }, { key: 'qr-all', e: '', l: 'كل قصار السور' }]
  });
})();
