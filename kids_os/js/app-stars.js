/* نجومي: مجموع النجوم وألبوم الملصقات التي ربحها الطفل من كل التطبيقات. */
(function () {
  var box;
  function build(body) { box = OS.el('<div></div>'); body.appendChild(box); return { enter: draw }; }

  function draw() {
    var all = [], got = 0;
    OS.each(OS.apps, function (a) { OS.each(a.awards || [], function (w) { all.push({ w: w, a: a }); if (OS.data.awards[w.key]) got++; }); });
    var h = '<div class="trophy">' + OS.icon('trophy') + '</div><div class="big-num">' + OS.data.stars + ' نجمة</div>' +
      '<div class="title2">ملصقاتي: ' + got + ' من ' + all.length + '</div><div class="sticker-grid">';
    // الملصق أيقونة التطبيق بلونه؛ المقفل رمادي بقفل
    OS.each(all, function (x) {
      var on = OS.data.awards[x.w.key];
      h += '<div class="sticker' + (on ? '' : ' locked') + '"><span class="em"' + (on ? ' style="background:' + x.a.color + ';box-shadow:0 4px 0 ' + x.a.shade + '"' : '') + '>' +
        OS.icon(on ? x.a.icon : 'lock') + '</span>' + x.w.l + '</div>';
    });
    box.innerHTML = h + '</div>';
  }

  OS.register({ id: 'stars', name: 'نجومي', icon: 'star', color: '#f59e0b', shade: '#b45309', build: build, scroll: true, dock: true });
})();
