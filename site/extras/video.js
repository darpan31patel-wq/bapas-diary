// Video Darshan plays inside the page (Darpan, 31 Oct 2026: "the youtube video still opens in another tab?").
// Every gold Video Darshan link on the site (Today, Calendar, Search, Travels, Places, the moments list, the Live now
// line, My favourites) opens the video in a dark frame over the page it was on, fading in. Close, Escape, a tap beside
// the frame or the phone's back button take it away and the page is exactly where it was. A moment starts at its second.
// Holding Ctrl, Cmd or Shift, or a middle click, still opens YouTube in a new tab as before.
(function () {
  'use strict';
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let box = null, back = null;
  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const parse = href => {
    try {
      const u = new URL(href, location.href), h = u.hostname.replace(/^www\.|^m\./, '');
      let id = null;
      if (h === 'youtu.be') id = u.pathname.slice(1).split('/')[0];
      else if (h === 'youtube.com' || h === 'youtube-nocookie.com') id = u.searchParams.get('v') || (/\/(?:embed|live|shorts)\/([^/?]+)/.exec(u.pathname) || [])[1];
      if (!id || !/^[\w-]{6,}$/.test(id)) return null;
      const t = /^(\d+)/.exec(u.searchParams.get('t') || u.searchParams.get('start') || '');
      return { id, t: t ? +t[1] : 0 };
    } catch (e) { return null; }
  };
  function play(id, t, title) {
    close(true);
    back = document.activeElement;
    box = document.createElement('div');
    box.className = 'bd-video'; box.setAttribute('role', 'dialog'); box.setAttribute('aria-modal', 'true'); box.setAttribute('aria-label', title || 'Video Darshan');
    box.innerHTML = `<div class="bd-vtop"><span class="bd-vname">${esc(title || 'Video Darshan')}</span><button type="button" class="bd-vclose">Close</button></div>` +
      `<div class="bd-vframe"><iframe src="https://www.youtube-nocookie.com/embed/${encodeURIComponent(id)}?autoplay=1&playsinline=1&rel=0${t ? '&start=' + t : ''}" ` +
      `title="${esc(title || 'Video Darshan')}" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe></div>`;
    document.body.append(box);
    document.documentElement.classList.add('bd-video-open');
    if (!reduce) requestAnimationFrame(() => requestAnimationFrame(() => box && box.classList.add('on'))); else box.classList.add('on');
    box.querySelector('.bd-vclose').focus();
    box.querySelector('.bd-vclose').addEventListener('click', () => close());
    box.addEventListener('click', e => { if (e.target === box) close(); });
    try { history.pushState({ bdVideo: id }, ''); } catch (e) {}
  }
  function close(quiet) {
    if (!box) return;
    const b = box; box = null;
    document.documentElement.classList.remove('bd-video-open');
    b.classList.remove('on');
    const gone = () => b.remove();
    reduce || quiet ? gone() : setTimeout(gone, 450);
    if (!quiet && history.state && history.state.bdVideo) { try { history.back(); } catch (e) {} }
    if (back && back.focus && document.contains(back)) back.focus();
    back = null;
  }
  addEventListener('popstate', () => { if (box) close(true); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && box) { e.preventDefault(); close(); } });
  document.addEventListener('click', e => {
    if (e.defaultPrevented || e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
    const a = e.target.closest && e.target.closest('a[href]');
    if (!a) return;
    const v = parse(a.getAttribute('href'));
    if (!v) return;
    e.preventDefault();
    const name = a.title || (a.closest('.bd-mr') && a.textContent.replace(/^\s*[\d:]+\s*/, '').trim()) || '';
    const menu = a.closest('.bd-moments'); if (menu) menu.remove();
    play(v.id, v.t, name);
  });
  window.BapaVideo = { play, close, parse };
})();
