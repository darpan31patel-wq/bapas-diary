// Phone redesign of Through the years (mockup). Only on phones.
(function () {
  if (innerWidth > 760) return;
  const R = document.documentElement, C = R.classList.contains('pr-c');
  // the year and place line, the most prominent words (like the Today cards)
  const yp = document.createElement('div'); yp.className = 'pr-yp';
  yp.innerHTML = '<span class="pr-y"></span><span class="pr-p"></span>';
  const infoL = document.querySelector('.info.l');
  infoL.prepend(yp);
  if (C) $('slot').append(infoL);   // look C: the year and place sit on the photo
  // the years row is the scroller itself: every year the same width, the knob moves through the days of the year it is in
  const days = $('days'), yrs = document.querySelector('.years');
  const track = document.createElement('div'); track.className = 'pr-track';
  const knob = document.createElement('i'); knob.className = 'pr-knob';
  days.before(track); days.hidden = true;
  if (C) { yrs.classList.add('pr-grid'); track.innerHTML = '<b class="pr-line"><s></s></b>'; } else track.append(yrs);
  track.append(knob);
  let spans = [];
  const ys = () => [...years.keys()];
  function where() {
    const x = list[idx]; if (!x) return;
    const k = ys().indexOf(x.y), sp = spans[k]; if (!sp) return;
    const f = sp[1] > sp[0] ? (idx - sp[0]) / (sp[1] - sp[0]) : .5;
    const pos = (k + f * .999) / spans.length * 100;
    knob.style.left = pos + '%';
    track.style.setProperty('--pos', pos + '%');
  }
  function at(e) {
    const r = track.getBoundingClientRect(), u = Math.max(0, Math.min(.9999, (e.clientX - r.left) / r.width));
    const k = Math.floor(u * spans.length), f = u * spans.length - k, sp = spans[k];
    stop(); show(Math.round(sp[0] + f * (sp[1] - sp[0])), true);
  }
  // a tap on a year opens that year on its best darshan, like the year buttons; a slide moves through the days
  let down = null;
  track.addEventListener('pointerdown', e => { if (C) { down = { x: e.clientX, moved: true }; at(e); } else down = { x: e.clientX, moved: false }; track.setPointerCapture(e.pointerId); });
  track.addEventListener('pointermove', e => { if (!down) return; if (Math.abs(e.clientX - down.x) > 6) down.moved = true; if (down.moved) at(e); });
  track.addEventListener('pointerup', e => {
    if (down && !down.moved) { const r = track.getBoundingClientRect(); goYear(ys()[Math.min(spans.length - 1, Math.floor((e.clientX - r.left) / r.width * spans.length))]); }
    down = null;
  });
  track.addEventListener('pointercancel', () => { down = null; });
  const osh = show;
  window.show = function (i, fast, calm) { osh(i, fast, calm); where(); };
  const of = facts;
  window.facts = function (x) {
    of(x);
    R.style.setProperty('--pr-photo', `url("${photo(x)}")`);
    yp.querySelector('.pr-y').textContent = x.y;
    yp.querySelector('.pr-p').textContent = x.place;
    $('date').textContent = (x.to ? rangeDate(x.day, x.to) : longDate(x.day)).replace(/^\w+day /, '');
  };
  const os = setEra;
  window.setEra = function (e) {
    os(e);
    spans = ys().map(y => { let a = -1, b = -1; list.forEach((x, i) => { if (x.y === y) { if (a < 0) a = i; b = i; } }); return [a, b]; });
    track.style.setProperty('--n', spans.length);
    where();
  };
  for (const b of document.querySelectorAll('.tab')) b.onclick = () => setEra(b.dataset.era);
  const P = '<svg viewBox="0 0 18 18" width="18" height="18"><path d="M4 2l12 7-12 7z" fill="currentColor"/></svg>', Z = '<svg viewBox="0 0 18 18" width="18" height="18"><path d="M3 2h4v14H3zM11 2h4v14h-4z" fill="currentColor"/></svg>';
  $('play').innerHTML = P;
  const ost = start, osp = stop;
  window.start = function () { ost(); $('play').innerHTML = Z; };
  window.stop = function () { const was = playing; osp(); if (was) $('play').innerHTML = P; };
  $('play').onclick = () => playing ? stop() : start();
  // the photo fills the whole space given to it, edge to edge, with a soft blur of itself behind
  window.fit = function () { const sl = $('frame').parentNode, cs = getComputedStyle(sl); $('frame').style.width = (sl.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight)) + 'px'; $('frame').style.height = sl.clientHeight + 'px'; };
  setEra(era);
  requestAnimationFrame(() => { fit(); if (front.day) place(front, front.day, front.classList.contains('rest')); });
})();
