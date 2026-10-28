// Phone redesign of Travels (mockup). Only on phones: the year and place on one line, In / Flying to beside the dates.
(function () {
  if (innerWidth > 760) return;
  const $ = id => document.getElementById(id);
  const yp = document.createElement('div'); yp.className = 'pr-yp';
  $('year').before(yp); yp.append($('year'), $('place'));
  const sub = $('country').parentNode; sub.classList.add('pr-sub'); sub.prepend($('status'));
  document.querySelector('.story').append(yp, sub, $('more'));
})();
