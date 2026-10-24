/* أيقونات النظام: رسوم خطية موحّدة (24×24) بدل الرموز التعبيرية التي يختلف شكلها بين الأجهزة. */
OS.ICONS = {
  quran: '<path d="M3 5.5c2.5-1.2 5.5-1 9 1 3.5-2 6.5-2.2 9-1V19c-2.5-1.2-5.5-1-9 1-3.5-2-6.5-2.2-9-1z"/><path d="M12 6.5V20"/>',
  pencil: '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M14 6l4 4"/>',
  bulb: '<path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 0 0-3.8 10.6c.6.6.8 1.3.8 2.4h6c0-1.1.2-1.8.8-2.4A6 6 0 0 0 12 3z"/>',
  drop: '<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/>',
  boat: '<path d="M3 15h18l-2.5 5h-13z"/><path d="M12 4v11"/><path d="M12 5l6 8h-6"/>',
  magnet: '<path d="M6 3v9a6 6 0 0 0 12 0V3h-4v9a2 2 0 0 1-4 0V3z"/><path d="M6 7h4M14 7h4"/>',
  palette: '<path d="M12 3a9 9 0 0 0 0 18c1.4 0 2-.9 2-1.9 0-1.2-1-1.6-1-2.6S13.8 15 15 15h2a4 4 0 0 0 4-4c0-4.4-4-8-9-8z"/><circle cx="7.5" cy="11" r="1.2"/><circle cx="10" cy="7" r="1.2"/><circle cx="15" cy="7.5" r="1.2"/>',
  sprout: '<path d="M12 21v-9"/><path d="M12 12C12 8 9 6 5 6c0 4 3 6 7 6z"/><path d="M12 10c0-3 2-5 6-5 0 3-2 5-6 5z"/>',
  shadow: '<circle cx="7" cy="7" r="3"/><path d="M15 8v12"/><path d="M15 20h6" stroke-width="3.5"/><path d="M3 20h9"/>',
  fall: '<circle cx="12" cy="6" r="3.5"/><path d="M12 12v8M8.5 16.5L12 20l3.5-3.5"/>',
  cloud: '<path d="M7 15a4 4 0 0 1 .4-8 5 5 0 0 1 9.6 1.5A3.5 3.5 0 0 1 16.5 15z"/><path d="M9 18l-1 2.5M13 18l-1 2.5M17 18l-1 2.5"/>',
  scale: '<path d="M12 4v16M8 20h8M5 7h14"/><path d="M5 7l-3 6a3 3 0 0 0 6 0z"/><path d="M19 7l-3 6a3 3 0 0 0 6 0z"/>',
  quiz: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .8-1 1.5v.7"/><path d="M12 17h.01"/>',
  star: '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/>',
  gear: '<path d="M4 6h9M17 6h3M4 12h3M11 12h9M4 18h11M19 18h1"/><circle cx="15" cy="6" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="17" cy="18" r="2"/>',
  back: '<path d="M9 6l6 6-6 6"/>',
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
  reset: '<path d="M4 12a8 8 0 1 0 2.4-5.7"/><path d="M4 4v4h4"/>',
  trophy: '<path d="M8 4h8v6a4 4 0 0 1-8 0z"/><path d="M8 6H5a3 3 0 0 0 3 4M16 6h3a3 3 0 0 1-3 4"/><path d="M12 14v4M8 21h8M9 18h6"/>'
};

// يعيد رسم الأيقونة جاهزاً للإدراج
OS.icon = function (name, cls) {
  return '<svg class="ic' + (cls ? ' ' + cls : '') + '" viewBox="0 0 24 24">' + (OS.ICONS[name] || '') + '</svg>';
};
