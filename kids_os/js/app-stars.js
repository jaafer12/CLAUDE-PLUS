/* نجومي: مجموع النجوم وألبوم الملصقات التي ربحها الطفل من كل التطبيقات. */
(function () {
  var box;
  function build(body) { box = OS.el('<div></div>'); body.appendChild(box); return { enter: draw }; }

  function draw() {
    var all = [], got = 0;
    OS.each(OS.apps, function (a) { OS.each(a.awards || [], function (w) { all.push(w); if (OS.data.awards[w.key]) got++; }); });
    var h = '<div class="trophy">🏆</div><div class="big-num">⭐ ' + OS.data.stars + '</div>' +
      '<div class="title2">ملصقاتي: ' + got + ' من ' + all.length + '</div><div class="sticker-grid">';
    OS.each(all, function (w) {
      var on = OS.data.awards[w.key];
      h += '<div class="sticker' + (on ? '' : ' locked') + '"><span class="em">' + (on ? w.e : '🔒') + '</span>' + w.l + '</div>';
    });
    box.innerHTML = h + '</div>';
    OS.say('عندك ' + OS.data.stars + ' نجمة، و ' + got + ' ملصقات');
  }

  OS.register({ id: 'stars', name: 'نجومي', icon: '⭐', color: '#b26a00', build: build, scroll: true, dock: true });
})();
