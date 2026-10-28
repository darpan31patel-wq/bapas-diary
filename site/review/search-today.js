// Mockup only: Search opens on this day in every year instead of 1999 (Darpan, 28 Oct 2026). website-search-mockup.yml
// makes these swaps inside the test browser; nothing on the site changes.
module.exports = [
  ["const START_YEAR = '1999';", "const START_YEAR = 'today';"],
  ["  if (START_YEAR && !linked && !$('q').value.trim() && !$('year').value) { $('year').value = START_YEAR; search(); }",
   "  if (START_YEAR && !linked && !$('q').value.trim() && !$('year').value && !$('month').value) { if (START_YEAR === 'today') { const t = new Date(); $('month').value = String(t.getMonth() + 1).padStart(2, '0'); $('day').value = String(t.getDate()).padStart(2, '0'); } else $('year').value = START_YEAR; search(); }"],
];
