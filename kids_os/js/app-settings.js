/* إعدادات الأهل: محمية بسؤال حساب. الاسم، الخلفية، تصفير التقدّم، مصادر الصور والقرآن. */
(function () {
  var VERSION = '2.0.0';
  var WALLS = ['wp-sky', 'wp-night', 'wp-sea', 'wp-candy', 'wp-grass'];
  var box, answer = 0, typed = '';

  function build(body) { box = OS.el('<div></div>'); body.appendChild(box); return { enter: gate, leave: function () { box.innerHTML = ''; } }; }

  // ---------- بوابة الأهل ----------
  function gate() {
    var a = 6 + Math.floor(Math.random() * 4), b = 3 + Math.floor(Math.random() * 6);
    answer = a * b; typed = '';
    box.innerHTML = '<div class="title2" style="margin-top:30px">للأهل فقط</div>' +
      '<div class="q-text">كم يساوي ' + a + ' × ' + b + ' ؟</div><div class="big-num" id="gateShow" style="min-height:76px;direction:ltr">&nbsp;</div>';
    var pad = OS.el('<div class="row" style="max-width:420px;margin:0 auto;direction:ltr"></div>');
    var keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '⌫', '0', '✓'];
    OS.each(keys, function (k) {
      var n = OS.el('<button class="btn ' + (k === '✓' ? 'btn-green' : k === '⌫' ? 'btn-red' : 'btn-white') + '" style="width:110px;font-size:30px">' + k + '</button>');
      OS.tap(n, function () { key(k); });
      pad.appendChild(n);
    });
    box.appendChild(pad);
  }
  function key(k) {
    if (k === '⌫') typed = typed.slice(0, -1);
    else if (k === '✓') { if (+typed === answer) return panel(); gate(); return; }
    else if (typed.length < 3) typed += k;
    OS.$('gateShow').innerHTML = typed || '&nbsp;';
  }

  // ---------- لوحة الإعدادات ----------
  function row(label, ctl) {
    var r = OS.el('<div class="set-row"><div>' + label + '</div><div class="ctl"></div></div>');
    if (ctl) r.lastChild.appendChild(ctl);
    box.appendChild(r); return r;
  }
  function button(label, cls, fn) { var b = OS.el('<button class="btn ' + cls + '">' + label + '</button>'); OS.tap(b, fn); return b; }

  function panel() {
    box.innerHTML = '<div class="title2" style="margin-top:14px">إعدادات الأهل</div>';

    var name = OS.el('<span><input class="modal-input" style="margin:0;width:220px" maxlength="16" placeholder="اسم الطفل"></span>');
    name.firstChild.value = OS.data.name || '';
    name.appendChild(button('حفظ', 'btn-green', function () {
      OS.data.name = name.firstChild.value.replace(/[<>&"]/g, '').trim(); OS.save(); name.firstChild.blur();
      OS.ok('أهلاً ' + (OS.data.name || 'بك') + '!');
    }));
    row('اسم الطفل', name);

    var walls = OS.el('<span></span>');
    OS.each(WALLS, function (w) {
      var n = OS.el('<span class="wp-pick ' + w + (OS.data.wallpaper === w ? ' on' : '') + '"></span>');
      OS.tap(n, function () { OS.setWallpaper(w); panel(); });
      walls.appendChild(n);
    });
    row('الخلفية', walls);

    row('تصفير النجوم والملصقات', button('تصفير', 'btn-red', function () {
      OS.ask('هل تريد حذف كل النجوم والملصقات؟', [
        { label: 'نعم، احذف', cls: 'btn-red', fn: function () {
          var d = OS.data; d.stars = 0; d.awards = {}; d.traced = {}; d.quran = {};
          OS.save(); OS.refreshStars(); OS.ok('بدأنا من جديد');
        } },
        { label: 'لا', cls: 'btn-white' }
      ]);
    }));

    var n = 0; for (var k in OS.photos) n++;
    if (n) row('مصادر الصور (' + n + ')', button('عرض', 'btn-white', credits));

    var tip = OS.el('<div class="info" style="padding-left:18px;font-size:19px"><b>لقفل الآيباد على نظام نجوم (الوصول الموجَّه):</b><br>' +
      '١. الإعدادات ← عام ← تسهيلات الاستخدام ← الوصول الموجَّه: شغّله وضع رمزاً سرياً.<br>' +
      '٢. افتح «نجوم» ثم اضغط زر الشاشة الرئيسية (الزر الدائري) <b>ثلاث مرات</b> بسرعة ← ابدأ.<br>' +
      '٣. للخروج: اضغط الزر ثلاث مرات وأدخل الرمز.<br><br>' +
      'الإصدار ' + VERSION + ' — يعمل بلا إنترنت بعد أول فتح.</div>');
    box.appendChild(tip);
  }

  // الصور من ويكيميديا كومنز برخص حرة؛ نذكر المصوّر والرخصة لكل صورة
  function credits() {
        box.innerHTML = '<div class="title2" style="margin-top:14px">مصادر الصور — Wikimedia Commons</div>';
    var back = button('رجوع', 'btn-white', panel);
    box.appendChild(OS.el('<div class="row"></div>')).appendChild(back);
    var keys = []; for (var k in OS.photos) keys.push(k);
    keys.sort();
    OS.each(keys, function (k) {
      var c = OS.photos[k];
      box.appendChild(OS.el('<div class="credit">' + OS.pic(k, '', '') + ' ' + esc(c.file) + ' — ' + esc(c.author) + ' (' + esc(c.license) + ')</div>'));
    });
  }
  function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

  OS.register({ id: 'settings', name: 'الأهل', icon: 'gear', color: '#64748b', shade: '#334155', build: build, scroll: true, dock: true });
})();
