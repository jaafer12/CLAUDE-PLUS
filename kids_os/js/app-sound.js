/* الصوت: إكسيليفون. القضيب القصير يهتز أسرع فيعطي صوتاً حاداً، والطويل صوتاً غليظاً. */
(function () {
  var NOTES = [
    ['دو', 262, '#e53935'], ['ري', 294, '#fb8c00'], ['مي', 330, '#fdd835'], ['فا', 349, '#43a047'],
    ['صول', 392, '#1e88e5'], ['لا', 440, '#3949ab'], ['سي', 494, '#8e24aa'], ['دو', 523, '#d81b60']
  ];
  // «نجمة صغيرة تلمع» بأرقام القضبان
  var SONG = [0, 0, 4, 4, 5, 5, 4, 3, 3, 2, 2, 1, 1, 0];
  var bars = [], info, songAt = -1, played = {};

  function build(body) {
    var wrap = OS.el('<div></div>');
    info = OS.info('اضغط على القضبان: <b>القصير</b> يعطي صوتاً <b>حاداً</b>، و<b>الطويل</b> صوتاً <b>غليظاً</b>.');
    var xylo = OS.el('<div class="xylo"></div>');
    OS.each(NOTES, function (n, i) {
      var b = OS.el('<div class="bar" style="height:' + (300 - i * 24) + 'px;background:' + n[2] + '"></div>');
      // نعزف عند بداية اللمس فوراً كما في الآلة الحقيقية
      b.addEventListener('touchstart', function (e) { e.preventDefault(); hit(i); }, false);
      b.addEventListener('mousedown', function () { hit(i); }, false);
      bars.push(b); xylo.appendChild(b);
    });
    var row = OS.el('<div class="row"></div>');
    var songBtn = OS.el('<button class="btn btn-orange">⭐ اعزف «نجمة صغيرة»</button>');
    OS.tap(songBtn, startSong);
    row.appendChild(songBtn);
    wrap.appendChild(info); wrap.appendChild(xylo); wrap.appendChild(row);
    body.appendChild(wrap);
    return { enter: function () { OS.say(info.lastChild.innerHTML.replace(/<[^>]+>/g, ' ')); }, leave: stopSong };
  }

  function hit(i) {
    OS.note(NOTES[i][1]);
    var b = bars[i]; b.className = b.className.replace(' hit', '') + ' hit';
    setTimeout(function () { b.className = b.className.replace(' hit', ''); }, 140);
    played[i] = 1;
    var n = 0; for (var k in played) n++;
    if (n === NOTES.length && songAt < 0) OS.award('snd-all', '🎵', 'جرّبت كل الأصوات، من الغليظ إلى الحاد!');
    if (songAt >= 0) follow(i);
  }

  function startSong() {
    OS.sfx('click'); songAt = 0; mark();
    OS.say('اضغط على القضيب الذي يلمع');
  }
  function stopSong() { songAt = -1; mark(); }
  function mark() {
    OS.each(bars, function (b, i) {
      b.className = 'bar' + (songAt >= 0 && SONG[songAt] === i ? ' next' : '');
    });
  }
  function follow(i) {
    if (SONG[songAt] !== i) return;
    songAt++;
    if (songAt >= SONG.length) {
      songAt = -1; mark();
      setTimeout(function () { if (!OS.award('snd-song', '⭐', 'عزفت «نجمة صغيرة»! أنت موسيقي')) OS.toast('🎶', 'أحسنت العزف!'); }, 500);
      return;
    }
    mark();
  }

  OS.register({
    id: 'sound', name: 'الصوت', icon: '🎵', color: '#00695c', build: build, scroll: true,
    awards: [{ key: 'snd-all', e: '🎵', l: 'كل الأصوات' }, { key: 'snd-song', e: '⭐', l: 'الموسيقي الصغير' }]
  });
})();
