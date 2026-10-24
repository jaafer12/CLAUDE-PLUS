/* أيقونات النظام: رسوم خطية موحّدة (24×24) بدل الرموز التعبيرية التي يختلف شكلها بين الأجهزة. */
OS.ICONS = {
  quran: '<path d="M3 5.5c2.5-1.2 5.5-1 9 1 3.5-2 6.5-2.2 9-1V19c-2.5-1.2-5.5-1-9 1-3.5-2-6.5-2.2-9-1z"/><path d="M12 6.5V20"/>',
  pencil: '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M14 6l4 4"/>',
  star: '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/>',
  gear: '<path d="M4 6h9M17 6h3M4 12h3M11 12h9M4 18h11M19 18h1"/><circle cx="15" cy="6" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="17" cy="18" r="2"/>',
  back: '<path d="M9 6l6 6-6 6"/>',
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
  reset: '<path d="M4 12a8 8 0 1 0 2.4-5.7"/><path d="M4 4v4h4"/>',
  home: '<path d="M3 11l9-8 9 8"/><path d="M5 10v10h5v-6h4v6h5V10"/>',
  help: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .8-1 1.5v.7"/><path d="M12 17h.01"/>',
  trash: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
  eraser: '<path d="M7 20h13"/><path d="M4.5 15.5l9-9a2 2 0 0 1 2.8 0l2.2 2.2a2 2 0 0 1 0 2.8L12 18H7z"/>',
  undo: '<path d="M9 14L4 9l5-5"/><path d="M4 9h11a5 5 0 0 1 0 10h-3"/>',
  shapes: '<circle cx="7" cy="7" r="4"/><path d="M17 3l4 7h-8z"/><rect x="4" y="14" width="7" height="7" rx="1"/><path d="M17.5 14.5l1 2 2.2.3-1.6 1.5.4 2.2-2-1-2 1 .4-2.2-1.6-1.5 2.2-.3z"/>',
  palette: '<path d="M12 3a9 9 0 1 0 0 18c1.2 0 2-.8 2-1.8 0-.5-.2-.9-.5-1.2-.3-.3-.5-.7-.5-1.2 0-1 .8-1.8 1.8-1.8H17a4 4 0 0 0 4-4c0-4.4-4-8-9-8z"/><circle cx="7.5" cy="11" r="1.2"/><circle cx="10" cy="7" r="1.2"/><circle cx="15" cy="7.5" r="1.2"/>',
  bucket: '<path d="M5 11l6-6 8 8-6 6a2 2 0 0 1-2.8 0L5 13.8a2 2 0 0 1 0-2.8z"/><path d="M5 11h14"/><path d="M8 3l3 2"/><path d="M20 16s1.5 2 1.5 3a1.5 1.5 0 0 1-3 0c0-1 1.5-3 1.5-3z"/>',
  brush: '<path d="M18.5 3.5l2 2L11 15l-2-2z"/><path d="M9 13c-2 0-3.5 1.5-3.5 3.5 0 1.2-.8 2.2-2 2.5 1 1 2.5 1.5 4 1.5 2.5 0 4-1.8 4-4z"/>',
  grid: '<rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/>',
  trophy: '<path d="M8 4h8v6a4 4 0 0 1-8 0z"/><path d="M8 6H5a3 3 0 0 0 3 4M16 6h3a3 3 0 0 1-3 4"/><path d="M12 14v4M8 21h8M9 18h6"/>'
};

// يعيد رسم الأيقونة جاهزاً للإدراج
OS.icon = function (name, cls) {
  return '<svg class="ic' + (cls ? ' ' + cls : '') + '" viewBox="0 0 24 24">' + (OS.ICONS[name] || '') + '</svg>';
};

// قلم تلوين مرسوم: رأس مدبّب وجسم باللون (يُستخدم في السبورة والتلوين)
OS.crayon = function (c) {
  return '<svg viewBox="0 0 40 100" width="46" height="112"><path d="M8 36 L20 4 L32 36 Z" fill="' + c + '"/>' +
    '<rect x="6" y="34" width="28" height="64" rx="8" fill="' + c + '"/><rect x="6" y="72" width="28" height="9" fill="#fff" opacity=".45"/></svg>';
};
