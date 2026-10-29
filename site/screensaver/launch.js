// The Screensaver button on the Today page of bapas-diary.com (Darpan, 29 Oct 2026: "a big screensaver button ... blurs
// everything in the background, and it'll say you are now entering screensaver state. And then when you press OK ...").
// Website only: nothing here touches the daily 2pm picture. tools/web_screensaver.py puts the button and this file on the
// Today page. OK fills the whole screen with /screensaver/ (true full screen where the browser allows it, the screen kept
// awake). Escape, or the ✕ inside the screensaver on a touch screen, brings the page back.
(function () {
  'use strict';
  const URL = '/screensaver/';
  const button = document.getElementById('screensaverButton');
  if (!button) return;
  const root = document.documentElement;
  let frame = null, lock = null, ask = null;

  function close() {
    removeEventListener('message', onMessage);
    document.removeEventListener('fullscreenchange', onFull);
    document.removeEventListener('webkitfullscreenchange', onFull);
    if (frame) { frame.remove(); frame = null; }
    root.classList.remove('ss-open');
    try { lock && lock.release(); } catch (e) {}
    lock = null;
    try { if (document.fullscreenElement) document.exitFullscreen(); else if (document.webkitFullscreenElement) document.webkitExitFullscreen(); } catch (e) {}
    button.focus();
  }
  const onMessage = e => { if (frame && e.source === frame.contentWindow && e.data && e.data.type === 'screensaver-exit') close(); };
  const onFull = () => { if (frame && !document.fullscreenElement && !document.webkitFullscreenElement) close(); };   // Escape leaves full screen: back to the page

  function open() {
    if (frame) return;
    frame = document.createElement('iframe');
    frame.src = URL;
    frame.allow = 'fullscreen; screen-wake-lock; geolocation';
    frame.title = 'Screensaver';
    frame.className = 'ss-frame';
    document.body.appendChild(frame);
    root.classList.add('ss-open');
    // full screen has to be asked for inside the tap itself
    try { const p = (root.requestFullscreen || root.webkitRequestFullscreen).call(root, { navigationUI: 'hide' }); if (p && p.catch) p.catch(() => {}); } catch (e) {}
    try { navigator.wakeLock && navigator.wakeLock.request('screen').then(l => { lock = l; }).catch(() => {}); } catch (e) {}
    addEventListener('message', onMessage);
    document.addEventListener('fullscreenchange', onFull);
    document.addEventListener('webkitfullscreenchange', onFull);
    frame.focus();
  }

  // "You are now entering screensaver state", over the page gone soft, with OK
  function confirm() {
    if (ask) return;
    ask = document.createElement('div');
    ask.className = 'ss-ask';
    ask.setAttribute('role', 'dialog'); ask.setAttribute('aria-modal', 'true'); ask.setAttribute('aria-labelledby', 'ss-ask-title');
    ask.innerHTML = '<div class="ss-box"><h2 id="ss-ask-title">You are now entering screensaver state</h2>' +
      '<p>The screen fills with darshan, On this day and Bapa’s latest photos, with the time, his day and a shlok.</p>' +
      '<p class="ss-small">To leave it, press Escape, or tap the ✕ on a touch screen.</p>' +
      '<div class="ss-row"><button type="button" class="pill solid" data-a="ok">OK</button><button type="button" class="pill" data-a="no">Not now</button></div></div>';
    document.body.appendChild(ask);
    root.classList.add('ss-asking');
    const done = () => { ask.remove(); ask = null; root.classList.remove('ss-asking'); };
    ask.addEventListener('click', e => {
      const b = e.target.closest('[data-a]');
      if (b && b.dataset.a === 'ok') { done(); open(); }
      else if (b || e.target === ask) { done(); button.focus(); }
    });
    ask.addEventListener('keydown', e => { if (e.key === 'Escape') { done(); button.focus(); } });
    ask.querySelector('[data-a=ok]').focus();
  }
  button.addEventListener('click', confirm);
  addEventListener('keydown', e => { if (frame && e.key === 'Escape') close(); });   // where there is no true full screen (iPhone)
  // the screensaver page is fetched quietly now, so the first tap opens it at once
  try { const l = document.createElement('link'); l.rel = 'prefetch'; l.href = URL; document.head.appendChild(l); } catch (e) {}
})();
